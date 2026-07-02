"""
Tests for the EDF-L1 CLI (main.py).

Exercises the Phase 7 CLI wiring end-to-end through the public ``main()``
entry point. Each test constructs a real ``ConfigLoader``-readable YAML and
invokes ``main(argv)``, asserting exit codes and side effects.

Network access is eliminated by stubbing adapter ``pre_flight`` (avoids HEAD
requests) and the download pipeline (avoids HTTP download). Everything else —
argparse, config load + validation, CLI overrides, orchestrator phases, and
manifest persistence — runs unmodified.

Test matrix (Phase 7 Technical Design §3.5):

    CLI-T1  valid config                     -> exit 0
    CLI-T2  missing config                   -> exit 2 (names the file)
    CLI-T3  --dry-run + valid config         -> exit 0, no files written
    CLI-T4  --board GSEB                     -> only GSEB adapter runs
    CLI-T5  malformed config                 -> exit 2 (cites the bad key)
    CLI-T6  --verify-only on empty CONTENT   -> exit 0
"""

from __future__ import annotations

from pathlib import Path

import main as main_module
from main import main, parse_args


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------


def _write_config(
    tmp_path: Path,
    content_root: Path,
    *,
    gseb: bool = True,
    ncert: bool = True,
    boards_section: bool = True,
    dry_run: bool = False,
) -> Path:
    """Write a valid two-board config to a temp path and return it.

    ``content_root`` is emitted with forward slashes so the YAML
    double-quoted scalar is not corrupted by Windows backslash escapes.
    """
    # Use forward slashes so YAML double-quote parsing is escape-safe on
    # Windows (a literal "C:\Users\..." would have \U etc. interpreted).
    root_str = str(content_root).replace("\\", "/")
    parts = [
        f'version: "1.0"',
        "general:",
        f'  content_root: "{root_str}"',
        f'  dry_run: {"true" if dry_run else "false"}',
    ]
    if boards_section:
        parts.extend([
            "boards:",
            "  gseb:",
            "    enabled: true",
            "  ncert:",
            "    enabled: true",
        ])
    parts.append("gseb:")
    parts.append("  textbooks:")
    if gseb:
        parts.append("    - std: \"09\"")
        parts.append('      subject: "maths"')
        parts.append('      medium: "gujarati"')
        parts.append('      language: "gu"')
        parts.append('      url: "https://example.org/gseb/g1.pdf"')
        parts.append('      filename: "g1.pdf"')
    parts.append("ncert:")
    parts.append("  textbooks:")
    if ncert:
        parts.append("    - code: \"IEMH1\"")
        parts.append('      std: "09"')
        parts.append('      subject: "maths"')
        parts.append('      medium: "english"')
        parts.append('      language: "en"')
    parts.append("download:")
    parts.append("  timeout_seconds: 5")
    parts.append("  max_retries: 1")
    parts.append("validation:")
    parts.append("  min_size_bytes: 1")
    text = "\n".join(parts) + "\n"
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _no_network(monkeypatch):
    """
    Stub adapter pre_flight (avoid HEAD requests).

    GSEBAdapter.pre_flight issues a network HEAD/GET against each textbook URL.
    We replace it with a no-op returning no issues so the pipeline proceeds to
    descriptor collection without touching the network.
    """
    from src.edf.adapters.base import BaseAdapter

    def _noop_pre_flight(self):
        return []

    monkeypatch.setattr(BaseAdapter, "pre_flight", _noop_pre_flight)


def _stub_download(monkeypatch):
    """Avoid HTTP download + atomic placement + manifest writes.

    Only ``_process_descriptor`` (the network/disk touch point) is stubbed;
    the real ``DownloadPipeline.run()`` aggregation and ``RunSummary``
    construction run unmodified — matching the established pattern in
    ``test_multiboard_integration.py``.
    """
    from src.edf.core.downloader import DownloadPipeline

    def _stub_process(self, descriptor, force=False):
        return {
            "status": "succeeded",
            "descriptor": descriptor,
            "details": {},
        }

    monkeypatch.setattr(
        DownloadPipeline, "_process_descriptor", _stub_process
    )


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

class TestArgumentParsing:
    def test_default_config_path(self):
        args = parse_args([])
        assert args.config == "config.yaml"
        assert args.dry_run is False
        assert args.board is None
        assert args.verify_only is False
        assert args.command == "run"

    def test_explicit_flags(self):
        args = parse_args(
            ["--config", "my.yaml", "--dry-run", "--board", "GSEB", "--verify-only"]
        )
        assert args.config == "my.yaml"
        assert args.dry_run is True
        assert args.board == "GSEB"
        assert args.verify_only is True

    def test_run_subcommand_optional(self):
        args = parse_args(["run"])
        assert args.command == "run"


# ---------------------------------------------------------------------------
# CLI-T2 / CLI-T5: configuration errors -> exit 2
# ---------------------------------------------------------------------------

class TestConfigErrors:
    def test_cli_t2_missing_config_returns_fatal(self, tmp_path, capsys):
        missing = tmp_path / "nope.yaml"
        code = main(["--config", str(missing)])
        assert code == 2
        captured = capsys.readouterr()
        assert "Config error" in captured.err
        assert str(missing) in captured.err

    def test_cli_t5_malformed_config_cites_key(self, tmp_path, capsys):
        path = tmp_path / "config.yaml"
        # version present but invalid -> ConfigValidationError names it.
        path.write_text('version: "2.0"\ngeneral:\n  content_root: "./C"\n',
                        encoding="utf-8")
        code = main(["--config", str(path)])
        assert code == 2
        captured = capsys.readouterr()
        assert "Config error" in captured.err
        # The message must cite the offending detail (version / config).
        assert "version" in captured.err.lower()


# ---------------------------------------------------------------------------
# CLI-T1: valid config -> exit 0
# ---------------------------------------------------------------------------

class TestValidRun:
    def test_cli_t1_valid_config_exit_zero(self, tmp_path, monkeypatch):
        _no_network(monkeypatch)
        _stub_download(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)
        code = main(["--config", str(config_path)])
        assert code == 0


# ---------------------------------------------------------------------------
# CLI-T3: --dry-run writes nothing under CONTENT
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_cli_t3_dry_run_writes_no_content(self, tmp_path, monkeypatch):
        _no_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        code = main(["--config", str(config_path), "--dry-run"])
        assert code == 0

        # No PDFs anywhere under CONTENT (only metadata dir may exist for logs).
        pdfs = list(content_root.rglob("*.pdf")) if content_root.exists() else []
        assert pdfs == [], f"dry-run wrote files: {pdfs}"


# ---------------------------------------------------------------------------
# CLI-T4: --board restricts to a single adapter
# ---------------------------------------------------------------------------

class TestBoardFilter:
    def test_cli_t4_board_filter_runs_only_gseb(self, tmp_path, monkeypatch):
        _no_network(monkeypatch)
        _stub_download(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        created_boards = []
        from src.edf.adapters.registry import AdapterRegistry

        real_create = AdapterRegistry.create

        def spy_create(self, board_name, config, http_client=None):
            created_boards.append(board_name)
            return real_create(self, board_name, config=config,
                               http_client=http_client)

        monkeypatch.setattr(AdapterRegistry, "create", spy_create)

        code = main(["--config", str(config_path), "--board", "GSEB"])
        assert code == 0
        assert created_boards == ["GSEB"], (
            f"expected only GSEB instantiated, got {created_boards}"
        )


# ---------------------------------------------------------------------------
# CLI-T6: --verify-only on empty CONTENT -> exit 0
# ---------------------------------------------------------------------------

class TestVerifyOnly:
    def test_cli_t6_verify_only_empty_content_exit_zero(
        self, tmp_path, monkeypatch
    ):
        _no_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        config_path = _write_config(tmp_path, content_root)

        code = main(["--config", str(config_path), "--verify-only"])
        assert code == 0


# ---------------------------------------------------------------------------
# CLI overrides: --dry-run forces the effective flag regardless of YAML
# ---------------------------------------------------------------------------

class TestCliOverrides:
    def test_dry_run_flag_forces_is_dry_run(self, tmp_path, monkeypatch):
        _no_network(monkeypatch)
        content_root = tmp_path / "CONTENT"
        # config has dry_run: false explicitly under general
        config_path = _write_config(tmp_path, content_root, dry_run=False)

        captured_dry_run = {}

        real_run = main_module.PipelineOrchestrator.run

        def spy_run(self, board=None, verify_only=False):
            captured_dry_run["is_dry_run"] = self._config.is_dry_run
            return real_run(self, board=board, verify_only=verify_only)

        monkeypatch.setattr(main_module.PipelineOrchestrator, "run", spy_run)

        main(["--config", str(config_path), "--dry-run"])
        assert captured_dry_run["is_dry_run"] is True
