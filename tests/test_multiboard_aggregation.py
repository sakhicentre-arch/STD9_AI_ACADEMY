"""
EDF-L1 Phase 6 — Multi-Board DownloadPipeline Aggregation.

Locks in the Phase 6 fix to ``DownloadPipeline.run()``: ``board_summaries``
must aggregate counts **per board** (per ``descriptor.board``) rather than
hardcoding a single "GSEB" key. This guarantees accurate summaries when
descriptors from multiple boards (GSEB, NCERT, ...) flow through the same
pipeline run.

These tests stub the actual download so they exercise only the aggregation
logic in ``run()`` — no network, no real files.
"""

from __future__ import annotations

from unittest.mock import patch

from src.edf.core.downloader import DownloadPipeline
from src.edf.models.data import DownloadDescriptor


def _desc(board: str, filename: str) -> DownloadDescriptor:
    return DownloadDescriptor(
        board=board,
        std="09",
        subject="maths",
        medium="english",
        language="en",
        url="http://127.0.0.1/dummy.pdf",
        filename=filename,
    )


def _make_pipeline() -> DownloadPipeline:
    # Minimal stubs: run() only touches _process_descriptor (mocked below)
    # plus the summary it builds. Storage/manifest are not consulted.
    return DownloadPipeline(
        storage_manager=object(),
        manifest_manager=object(),
        config={"download": {}, "validation": {}},
    )


class TestMultiBoardSummary:
    def test_single_board_gseb_key_present(self):
        pipeline = _make_pipeline()
        with patch.object(
            pipeline, "_process_descriptor",
            return_value={"status": "succeeded"},
        ):
            summary = pipeline.run([_desc("GSEB", "a.pdf")], run_id="r1")
        assert "GSEB" in summary.board_summaries
        bs = summary.board_summaries["GSEB"]
        assert bs == {"attempted": 1, "succeeded": 1, "skipped": 0, "failed": 0}

    def test_single_board_ncert_key_present(self):
        pipeline = _make_pipeline()
        with patch.object(
            pipeline, "_process_descriptor",
            return_value={"status": "succeeded"},
        ):
            summary = pipeline.run([_desc("NCERT", "b.pdf")], run_id="r1")
        assert "NCERT" in summary.board_summaries
        assert "GSEB" not in summary.board_summaries

    def test_multi_board_separate_buckets(self):
        pipeline = _make_pipeline()
        descs = [_desc("GSEB", "g1.pdf"), _desc("NCERT", "n1.pdf")]
        with patch.object(
            pipeline, "_process_descriptor",
            return_value={"status": "succeeded"},
        ):
            summary = pipeline.run(descs, run_id="r2")
        assert set(summary.board_summaries.keys()) == {"GSEB", "NCERT"}
        for b in ("GSEB", "NCERT"):
            assert summary.board_summaries[b] == {
                "attempted": 1, "succeeded": 1, "skipped": 0, "failed": 0,
            }

    def test_mixed_statuses_aggregate_per_board(self):
        pipeline = _make_pipeline()
        descs = [
            _desc("GSEB", "g1.pdf"),
            _desc("GSEB", "g2.pdf"),
            _desc("NCERT", "n1.pdf"),
        ]
        results = iter([
            {"status": "succeeded"},
            {"status": "failed"},
            {"status": "skipped"},
        ])

        def _fake_process(descriptor, force=False):
            return next(results)

        with patch.object(pipeline, "_process_descriptor", side_effect=_fake_process):
            summary = pipeline.run(descs, run_id="r3")

        gseb = summary.board_summaries["GSEB"]
        ncert = summary.board_summaries["NCERT"]
        assert gseb == {"attempted": 2, "succeeded": 1, "skipped": 0, "failed": 1}
        assert ncert == {"attempted": 1, "succeeded": 0, "skipped": 1, "failed": 0}
        # Totals still correct.
        assert (summary.attempted, summary.succeeded, summary.skipped,
                summary.failed) == (3, 1, 1, 1)

    def test_bucket_keys_match_status_values(self):
        # Confirms only the four documented bucket keys exist.
        pipeline = _make_pipeline()
        with patch.object(
            pipeline, "_process_descriptor",
            return_value={"status": "succeeded"},
        ):
            summary = pipeline.run([_desc("GSEB", "a.pdf")], run_id="r4")
        assert set(summary.board_summaries["GSEB"].keys()) == {
            "attempted", "succeeded", "skipped", "failed",
        }

    def test_unknown_board_key_aggregated_correctly(self):
        # Future board (e.g. CBSE) must be handled without code change.
        pipeline = _make_pipeline()
        with patch.object(
            pipeline, "_process_descriptor",
            return_value={"status": "succeeded"},
        ):
            summary = pipeline.run([_desc("CBSE", "c.pdf")], run_id="r5")
        assert summary.board_summaries["CBSE"]["succeeded"] == 1

    def test_empty_descriptor_list_no_boards(self):
        pipeline = _make_pipeline()
        with patch.object(pipeline, "_process_descriptor") as mocked:
            summary = pipeline.run([], run_id="r6")
        mocked.assert_not_called()
        assert summary.board_summaries == {}
        assert summary.attempted == 0
        # Existing contract: failed(0) == attempted(0) -> exit_code 2.
        # The aggregation fix does not change empty-run exit-code semantics.
        assert summary.exit_code == 2
