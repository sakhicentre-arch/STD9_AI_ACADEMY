"""
EDF-L1 Phase 6 — Multi-Board End-to-End Integration Test.

Exercises the complete multi-board wiring introduced in Step 4:

    PipelineOrchestrator
        -> AdapterRegistry (default_registry)
            -> GSEBAdapter + NCERTAdapter   (real adapters, instantiated once each)
        -> merged descriptors              (2 GSEB + 1 NCERT)
        -> DownloadPipeline                (real run(), stubbed network layer)
        -> RunSummary                      (per-board summaries)

Network / filesystem side effects are eliminated by stubbing:
    * each adapter's ``pre_flight``  -> returns [] (avoids HEAD requests)
    * ``DownloadPipeline._process_descriptor`` -> returns a canned status
      (avoids HTTP download, atomic placement, manifest writes)

The stubs are the *only* seams. Everything else — the orchestrator phases,
registry-driven discovery, the real adapter ``get_descriptors`` (descriptor
generation has no network dependency), the real ``DownloadPipeline.run()``
aggregation, and RunSummary construction — runs unmodified.

Asserted contract:
    * both adapters are instantiated exactly once (one ``create`` per board)
    * both adapters execute exactly once (pre_flight + get_descriptors)
    * descriptor lists are merged correctly (2 GSEB + 1 NCERT = 3)
    * DownloadPipeline.run is invoked exactly once with the merged list
    * RunSummary.board_summaries has correct per-board buckets
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from src.edf.adapters.registry import AdapterRegistry
from src.edf.core.downloader import DownloadPipeline
from src.edf.core.pipeline import PipelineOrchestrator


# ---------------------------------------------------------------------------
# Configuration: a minimal, deterministic two-board config.
# GSEB yields 2 descriptors; NCERT yields 1. No ``boards`` overrides needed
# beyond explicit enable flags — both boards are enabled.
# ---------------------------------------------------------------------------

_BASE_CONFIG = {
    "boards": {
        "gseb": {"enabled": True},
        "ncert": {"enabled": True},
    },
    "gseb": {
        "textbooks": [
            {
                "std": "09",
                "subject": "maths",
                "medium": "gujarati",
                "language": "gu",
                "url": "https://example.org/gseb/g1.pdf",
                "filename": "g1.pdf",
            },
            {
                "std": "09",
                "subject": "science",
                "medium": "gujarati",
                "language": "gu",
                "url": "https://example.org/gseb/g2.pdf",
                "filename": "g2.pdf",
            },
        ]
    },
    "ncert": {
        "textbooks": [
            {
                "code": "IEMH1",
                "std": "09",
                "subject": "maths",
                "medium": "english",
                "language": "en",
            },
        ]
    },
    "download": {"timeout_seconds": 5, "max_retries": 1},
    "validation": {"min_size_bytes": 1},
}


class TestMultiboardOrchestratorIntegration:
    def test_full_multiboard_path_registry_to_summary(self, tmp_path):
        # --- Build a lightweight ConfigLoader / Logger stand-in ---
        config_loader = SimpleNamespace(
            config=_BASE_CONFIG,
            content_root=str(tmp_path / "CONTENT"),
            edf_metadata_dir=".edf",
            is_force_overwrite=False,
        )
        logger_instance = SimpleNamespace(run_id="it_e2e_01")

        # --- Capture originals BEFORE patching so spies can delegate ---
        real_create = AdapterRegistry.create
        real_run = DownloadPipeline.run

        # --- Spy accumulators ---
        create_calls = []        # board names per instantiation
        exec_log = {}            # board -> {pre_flight, get_descriptors} counts
        run_calls = []           # descriptor lists passed to DownloadPipeline.run
        summary_holder = {}      # captured RunSummary

        def counting_create(self, board_name, config, http_client=None):
            """Wrap AdapterRegistry.create: instantiate once, count + spy."""
            adapter = real_create(
                self, board_name, config=config, http_client=http_client
            )
            create_calls.append(board_name)
            exec_log.setdefault(
                board_name, {"pre_flight": 0, "get_descriptors": 0}
            )

            # pre_flight -> stubbed to avoid network; just count.
            def pf():
                exec_log[board_name]["pre_flight"] += 1
                return []

            # get_descriptors -> real (no network); count + delegate.
            real_get_desc = adapter.get_descriptors

            def gd():
                exec_log[board_name]["get_descriptors"] += 1
                return real_get_desc()

            adapter.pre_flight = pf
            adapter.get_descriptors = gd
            return adapter

        def counting_run(self, descriptors, run_id="", force=False):
            """Wrap DownloadPipeline.run: record call, capture RunSummary."""
            run_calls.append(list(descriptors))
            summary = real_run(
                self, descriptors, run_id=run_id, force=force
            )
            summary_holder["summary"] = summary
            return summary

        def stub_process(self, descriptor, force=False):
            """Avoid HTTP download / placement / manifest writes."""
            return {
                "status": "succeeded",
                "descriptor": descriptor,
                "details": {},
            }

        # --- Run the orchestrator under the spies ---
        orchestrator = PipelineOrchestrator()
        orchestrator.initialize(config_loader, logger_instance)

        with patch.object(AdapterRegistry, "create", counting_create), \
                patch.object(DownloadPipeline, "run", counting_run), \
                patch.object(
                    DownloadPipeline, "_process_descriptor", stub_process
                ):
            result = orchestrator.run()

        # ===============================================================
        # 1. Both adapters instantiated EXACTLY ONCE
        # ===============================================================
        assert create_calls.count("GSEB") == 1
        assert create_calls.count("NCERT") == 1
        assert sorted(create_calls) == ["GSEB", "NCERT"]

        # ===============================================================
        # 2. Both adapters executed EXACTLY ONCE (pre_flight + get_desc)
        # ===============================================================
        assert exec_log["GSEB"] == {"pre_flight": 1, "get_descriptors": 1}
        assert exec_log["NCERT"] == {"pre_flight": 1, "get_descriptors": 1}

        # ===============================================================
        # 3. Descriptor lists merged correctly (2 GSEB + 1 NCERT = 3)
        # ===============================================================
        assert len(run_calls) == 1, "DownloadPipeline.run must be called once"
        merged = run_calls[0]
        assert len(merged) == 3
        boards = [d.board for d in merged]
        assert boards.count("GSEB") == 2
        assert boards.count("NCERT") == 1

        # ===============================================================
        # 4. DownloadPipeline invoked EXACTLY ONCE with the merged list
        #    (asserted above via len(run_calls) == 1 + merged contents)
        # ===============================================================

        # ===============================================================
        # 5. RunSummary contains correct per-board summaries
        # ===============================================================
        summary = summary_holder["summary"]
        assert summary.board_summaries["GSEB"] == {
            "attempted": 2, "succeeded": 2, "skipped": 0, "failed": 0,
        }
        assert summary.board_summaries["NCERT"] == {
            "attempted": 1, "succeeded": 1, "skipped": 0, "failed": 0,
        }

        # --- Orchestrator result reflects the summary faithfully ---
        assert result["exit_code"] == 0
        assert result["attempted"] == 3
        assert result["succeeded"] == 3
        assert result["failed"] == 0
        assert result["phases"]["collect"]["descriptors"] == 3
        assert result["phases"]["preflight"]["issues"] == 0
