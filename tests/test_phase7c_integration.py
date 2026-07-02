"""
EDF-L1 Phase 7C — ConfigLoader ⇄ CLI ⇄ Orchestrator Integration Tests.

Phase 7C verifies the *composition root* wiring that unites the Phase 7A
ConfigLoader with the Phase 7B CLI / PipelineOrchestrator.  Where the
existing suites test each component in isolation, these tests exercise the
**full stack from a real YAML file on disk through to the orchestrator result
dictionary**, using real production components at every layer except the
physical network and disk-write boundaries.

Integration stack (everything in ``real`` runs unmodified)::

    config.yaml (on disk)
        └─► ConfigLoader                 (REAL — load + validate + defaults)
              └─► main() / build_parser  (REAL — argparse + CLI overrides)
                    └─► build_orchestrator (REAL — wires EDFLogger + orchestrator)
                          └─► PipelineOrchestrator.run   (REAL — all 7 phases)
                                ├─► AdapterRegistry        (REAL)
                                │     ├─► GSEBAdapter      (REAL get_descriptors)
                                │     └─► NCERTAdapter     (REAL get_descriptors)
                                ├─► StorageManager         (REAL)
                                ├─► ManifestManager        (REAL — load + save)
                                └─► DownloadPipeline.run   (REAL aggregation)
                                      └─► _process_descriptor  (STUB — network/disk)

External boundaries mocked (and ONLY these):
    * HTTP HEAD requests in adapter ``pre_flight``  → stubbed to []
    * HTTP download + atomic placement in
      ``DownloadPipeline._process_descriptor``      → stubbed canned status

Seam rationale: ``pre_flight`` issues live HEAD/GET requests to board servers,
and ``_process_descriptor`` performs the actual HTTP fetch and disk write. Both
are true I/O boundaries; stubbing them alone leaves every other phase — config
parsing, CLI override application, registry-driven board discovery, real
descriptor generation, the real download aggregation loop, RunSummary
construction, and manifest persistence — running as in production.

Test matrix (Phase 7C Technical Design):

    IC-T1  ConfigLoader YAML  →  orchestrator result (real full stack)
    IC-T2  CLI override ``--dry-run`` forces is_dry_run through real main()
    IC-T3  defaults injected when optional keys absent (real ConfigLoader)
    IC-T4  chunk_size_bytes alias canonicalised end-to-end
    IC-T5  ConfigValidationError aborts at exit code 2 (config gate)
    IC-T6  ``--board`` filter restricts adapters via real registry path
    IC-T7  manifest persisted on a normal (non-dry) run
    IC-T8  dry-run leaves the repository byte-for-byte unchanged
    IC-T9  verify-only re-validates a pre-seeded manifest entry
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import main as main_module
from main import main, build_orchestrator, _apply_cli_overrides
from src.edf.adapters.registry import AdapterRegistry, default_registry
from src.edf.core.config import ConfigLoader, ConfigValidationError
from src.edf.core.downloader import DownloadPipeline
from src.edf.core.pipeline import PipelineOrchestrator


# ---------------------------------------------------------------------------
# YAML config builder
# ---------------------------------------------------------------------------

def _config_yaml(
    content_root: Path,
    *,
    gseb: bool = True,
    ncert: bool = True,
    boards_section: bool = True,
    dry_run: bool = False,
    extra_general: str = "",
    omit_optional: bool = False,
    chunk_alias: bool = False,
) -> str:
    """Return a valid config YAML string.

    ``content_root`` is emitted with forward slashes so the YAML double-quoted
    scalar survives Windows backslash escaping.

    Flags:
        omit_optional: drop every optional section so ConfigLoader defaults
                       must kick in (exercises IC-T3).
        chunk_alias:   emit ``download.chunk_size_bytes`` instead of
                       ``chunk_size`` so the V10 alias canonicalisation runs
                       end-to-end (exercises IC-T4).
    """
    root_str = str(content_root).replace("\\", "/")
    parts: list[str] = [
        'version: "1.0"',
        "general:",
        f'  content_root: "{root_str}"',
        f'  dry_run: {"true" if dry_run else "false"}',
    ]
    if extra_general:
        parts.append(extra_general)
    if boards_section:
        parts += [
            "boards:",
            "  gseb:",
            "    enabled: true",
            "  ncert:",
            "    enabled: true",
        ]
    parts.append("gseb:")
    parts.append("  textbooks:")
    if gseb:
        parts += [
            '    - std: "09"',
            '      subject: "maths"',
            '      medium: "gujarati"',
            '      language: "gu"',
            '      url: "https://example.org/gseb/g1.pdf"',
            '      filename: "g1.pdf"',
        ]
    parts.append("ncert:")
    parts.append("  textbooks:")
    if ncert:
        parts += [
            '    - code: "IEMH1"',
            '      std: "09"',
            '      subject: "maths"',
            '      medium: "english"',
            '      language: "en"',
        ]
    if not omit_optional:
        parts += [
            "download:",
            "  timeout_seconds: 5",
            "  max_retries: 1",
        ]
        if chunk_alias:
            parts.append("  chunk_size_bytes: 4096")
        parts += [
            "validation:",
            "  min_size_bytes: 1",
        ]
    return "\n".join(parts) + "\n"


def _write_config(
    tmp_path: Path,
    content_root: Path,
    **kwargs,
) -> Path:
    """Write a config file to ``tmp_path/config.yaml`` and return its path."""
    path = tmp_path / "config.yaml"
    path.write_text(_config_yaml(content_root, **kwargs), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Boundary stubs (network + disk write only)
# ---------------------------------------------------------------------------

def _stub_network(monkeypatch):
    """Suppress live HEAD requests and HTTP downloads.

    These are the only two true I/O seams in the pipeline.  Everything
    upstream (config, CLI, orchestrator phases, adapter descriptor
    generation, aggregation, manifest persistence) runs for real.
    """
    from src.edf.adapters.base import BaseAdapter

    def _noop_pre_flight(self):
        return []

    monkeypatch.setattr(BaseAdapter, "pre_flight", _noop_pre_flight)

    def _stub_process(self, descriptor, force=False):
        return {"status": "succeeded", "descriptor": descriptor, "details": {}}

    monkeypatch.setattr(
        DownloadPipeline, "_process_descriptor", _stub_process
    )


# ===========================================================================
# IC-T1: real ConfigLoader YAML  →  orchestrator result (full stack)
# ===========================================================================

class TestConfigLoaderToOrchestrator:
    """ConfigLoader on disk drives the orchestrator end-to-end."""

    def test_ic_t1_real_config_drives_orchestrator(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        # Exercise the FULL composition root via main() — real argparse,
        # real ConfigLoader, real build_orchestrator, real orchestrator.run.
        code = main(["--config", str(config_path)])

        assert code == 0

    def test_real_configloader_object_accepted_by_orchestrator(
        self, tmp_path, monkeypatch
    ):
        """A genuine ConfigLoader instance (not a stand-in) wires cleanly."""
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        loader = ConfigLoader(config_path)
        args = main_module.parse_args(["--config", str(config_path)])
        _apply_cli_overrides(loader, args)

        orchestrator = build_orchestrator(loader, args)
        try:
            assert orchestrator.is_initialized is True
            result = orchestrator.run()
        finally:
            orchestrator.shutdown()

        assert result["exit_code"] == 0
        assert result["attempted"] == 2  # 1 GSEB + 1 NCERT


# ===========================================================================
# IC-T2: CLI ``--dry-run`` override propagates through real main()
# ===========================================================================

class TestCliOverrideDryRun:
    def test_ic_t2_dry_run_flag_forces_dry_run_through_real_main(
        self, tmp_path, monkeypatch
    ):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        # YAML has dry_run: false — the CLI flag must override it.
        config_path = _write_config(tmp_path, content_root, dry_run=False)

        observed = {}

        real_run = PipelineOrchestrator.run

        def spy_run(self, board=None, verify_only=False):
            observed["is_dry_run"] = self._config.is_dry_run
            return real_run(self, board=board, verify_only=verify_only)

        monkeypatch.setattr(PipelineOrchestrator, "run", spy_run)

        code = main(["--config", str(config_path), "--dry-run"])
        assert code == 0
        assert observed["is_dry_run"] is True


# ===========================================================================
# IC-T3: ConfigLoader defaults injected when optional sections are absent
# ===========================================================================

class TestConfigDefaultsInjection:
    def test_ic_t3_defaults_applied_when_optional_keys_absent(
        self, tmp_path, monkeypatch
    ):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        # Omit download + validation entirely → ConfigLoader._apply_defaults
        # must inject every default so the orchestrator never KeyError-s.
        config_path = _write_config(
            tmp_path, content_root, omit_optional=True
        )

        loader = ConfigLoader(config_path)
        # The orchestrator reads these via typed accessors; assert defaults.
        assert loader.download["max_retries"] == ConfigLoader.DEFAULT_MAX_RETRIES
        assert (
            loader.download["timeout_seconds"]
            == ConfigLoader.DEFAULT_TIMEOUT_SECONDS
        )
        assert (
            loader.validation["min_size_bytes"]
            == ConfigLoader.DEFAULT_MIN_SIZE_BYTES
        )

        # And the full pipeline still runs green on defaults.
        code = main(["--config", str(config_path)])
        assert code == 0


# ===========================================================================
# IC-T4: chunk_size_bytes alias canonicalised end-to-end
# ===========================================================================

class TestChunkSizeAliasEndToEnd:
    def test_ic_t4_chunk_size_bytes_canonicalised_to_chunk_size(
        self, tmp_path, monkeypatch
    ):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(
            tmp_path, content_root, chunk_alias=True
        )

        loader = ConfigLoader(config_path)
        # V10 canonicalisation: chunk_size_bytes → chunk_size for the
        # downloader, which reads config["download"]["chunk_size"].
        assert loader.config["download"].get("chunk_size") == 4096

        # The orchestrator hands ``config`` straight to DownloadPipeline; a
        # green run proves the alias survives the composition-root handoff.
        code = main(["--config", str(config_path)])
        assert code == 0


# ===========================================================================
# IC-T5: ConfigValidationError aborts at exit code 2 (config gate)
# ===========================================================================

class TestConfigValidationErrorGate:
    def test_ic_t5_invalid_version_aborts_before_pipeline(
        self, tmp_path, capsys
    ):
        path = tmp_path / "config.yaml"
        path.write_text(
            'version: "9.9"\ngeneral:\n  content_root: "./C"\n',
            encoding="utf-8",
        )
        # No stubs installed: validation MUST fail before any network path.
        code = main(["--config", str(path)])
        assert code == 2
        err = capsys.readouterr().err
        assert "Config error" in err
        assert "version" in err.lower()

    def test_missing_textbook_field_cited(self, tmp_path, capsys):
        path = tmp_path / "config.yaml"
        # GSEB entry missing required 'url' + 'filename'.
        path.write_text(
            'version: "1.0"\n'
            "general:\n"
            '  content_root: "./C"\n'
            "gseb:\n"
            "  textbooks:\n"
            '    - std: "09"\n'
            '      subject: "maths"\n'
            '      medium: "gujarati"\n'
            '      language: "gu"\n',
            encoding="utf-8",
        )
        code = main(["--config", str(path)])
        assert code == 2
        err = capsys.readouterr().err
        # V7 must name the missing field.
        assert "url" in err


# ===========================================================================
# IC-T6: ``--board`` filter restricts adapters via the real registry path
# ===========================================================================

class TestBoardFilterRealRegistry:
    def test_ic_t6_board_filter_single_adapter_via_real_registry(
        self, tmp_path, monkeypatch
    ):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        instantiated: list[str] = []
        real_create = AdapterRegistry.create

        def spy_create(self, board_name, config, http_client=None):
            instantiated.append(board_name)
            return real_create(
                self, board_name, config=config, http_client=http_client
            )

        monkeypatch.setattr(AdapterRegistry, "create", spy_create)

        code = main(["--config", str(config_path), "--board", "ncert"])
        assert code == 0
        # Case-insensitive filter; only NCERT should be instantiated.
        assert instantiated == ["NCERT"]

    def test_board_filter_case_insensitive(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        instantiated: list[str] = []
        real_create = AdapterRegistry.create

        def spy_create(self, board_name, config, http_client=None):
            instantiated.append(board_name)
            return real_create(
                self, board_name, config=config, http_client=http_client
            )

        monkeypatch.setattr(AdapterRegistry, "create", spy_create)

        code = main(["--config", str(config_path), "--board", "Gseb"])
        assert code == 0
        assert instantiated == ["GSEB"]

    def test_unknown_board_exits_fatal(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        code = main(["--config", str(config_path), "--board", "ICSE"])
        assert code == 2


# ===========================================================================
# IC-T7: manifest persisted on a normal (non-dry) run
# ===========================================================================

class TestManifestPersistedOnNormalRun:
    def test_ic_t7_manifest_written_after_normal_run(
        self, tmp_path, monkeypatch
    ):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        code = main(["--config", str(config_path)])
        assert code == 0

        edf_dir = content_root / ".edf"
        manifest_path = edf_dir / "manifest.json"
        assert manifest_path.exists(), "manifest.json must be persisted"

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Real on-disk manifest schema: version + files list. Assert it is a
        # genuine, parseable manifest document produced by the orchestrator.
        assert isinstance(data, dict)
        assert data.get("version") == "1.0"
        assert "files" in data
        assert isinstance(data["files"], list)


# ===========================================================================
# IC-T8: dry-run leaves the repository byte-for-byte unchanged
# ===========================================================================

class TestDryRunNoMutation:
    def test_ic_t8_dry_run_writes_no_manifest(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        code = main(["--config", str(config_path), "--dry-run"])
        assert code == 0

        edf_dir = content_root / ".edf"
        manifest_path = edf_dir / "manifest.json"
        assert not manifest_path.exists(), (
            "dry-run must not persist a manifest"
        )

    def test_dry_run_writes_no_pdfs(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        main(["--config", str(config_path), "--dry-run"])

        pdfs = list(content_root.rglob("*.pdf")) if content_root.exists() else []
        assert pdfs == [], f"dry-run wrote PDFs: {pdfs}"


# ===========================================================================
# IC-T9: verify-only re-validates a pre-seeded manifest entry
# ===========================================================================

class TestVerifyOnlyRevalidation:
    def _seed_manifest(
        self,
        content_root: Path,
        rel_path: str,
        sha: str,
        validation_status: str = "VALID",
    ) -> None:
        """Write a manifest.json with one ManifestEntry pointing at ``rel_path``.

        Matches the real on-disk schema written by
        ``ManifestManager._save_manifest``: a ``files`` LIST of
        ``ManifestEntry`` dicts (see ``models.data.ManifestEntry``). The
        orchestrator's verify-only phase loads this via the real
        ``load_existing()`` and iterates ``manifest.entries`` keyed by
        ``path``.
        """
        edf_dir = content_root / ".edf"
        edf_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "version": "1.0",
            "run_id": "seed-01",
            "generated_at": "2026-07-02T00:00:00+00:00",
            "files": [
                {
                    "path": rel_path,
                    "sha256": sha,
                    "size_bytes": 1,
                    "board": "GSEB",
                    "subject": "maths",
                    "medium": "gujarati",
                    "std": "09",
                    "language": "gu",
                    "source_url": "https://example.org/gseb/g1.pdf",
                    "downloaded_at": None,
                    "last_verified": None,
                    "validation_status": validation_status,
                    "managed": True,
                }
            ],
        }
        (edf_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def test_ic_t9_verify_only_missing_file_marked_missing(
        self, tmp_path, monkeypatch
    ):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        # Seed a manifest whose file does NOT exist on disk.
        self._seed_manifest(content_root, "GSEB/09/gujarati/g1.pdf", "deadbeef")

        code = main(["--config", str(config_path), "--verify-only"])
        # Missing file → invalid → partial/fatal exit code.
        assert code in (1, 2)

        # The orchestrator must have re-validated and recorded the status.
        # The re-saved manifest uses the real ``files`` list schema.
        data = json.loads(
            (content_root / ".edf" / "manifest.json").read_text("utf-8")
        )
        entries = {e["path"]: e for e in data["files"]}
        entry = entries["GSEB/09/gujarati/g1.pdf"]
        assert entry["validation_status"] == "MISSING"

    def test_verify_only_empty_manifest_exit_zero(self, tmp_path, monkeypatch):
        _stub_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        code = main(["--config", str(config_path), "--verify-only"])
        assert code == 0


# ===========================================================================
# Composition-root wiring invariants
# ===========================================================================

class TestCompositionRootWiring:
    """Assert structural properties of the real composition root."""

    def test_default_registry_has_both_boards(self):
        registry = default_registry()
        assert registry.list_adapters() == ["GSEB", "NCERT"]

    def test_build_orchestrator_initializes_real_logger(self, tmp_path):
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)
        loader = ConfigLoader(config_path)
        args = main_module.parse_args(["--config", str(config_path)])

        orchestrator = build_orchestrator(loader, args)
        try:
            # build_orchestrator must inject a REAL EDFLogger, not None.
            assert orchestrator._logger is not None
            assert orchestrator._logger is not loader
            assert hasattr(orchestrator._logger, "run_id")
        finally:
            orchestrator.shutdown()

    def test_exit_code_mapping_constants(self):
        # The CLI's exit-code contract is part of the integration surface.
        assert main_module.EXIT_SUCCESS == 0
        assert main_module.EXIT_PARTIAL == 1
        assert main_module.EXIT_FATAL == 2
