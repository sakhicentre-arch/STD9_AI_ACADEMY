"""
EDF-L1 Phase 5 — Staged Integration Verification.

Runs the full GSEB pipeline against a locally-served real PDF, broken into
9 independent, sequentially-ordered stages. Stages share a single session
fixture so each stage asserts a distinct slice of the same end-to-end run.

Stages:
    3.1 Adapter initialization
    3.2 Descriptor generation
    3.3 DownloadPipeline execution
    3.4 HTTP download verification
    3.5 PDF validation
    3.6 SHA-256 registration
    3.7 StorageManager verification
    3.8 ManifestManager verification
    3.9 RunSummary verification

Run with ordering preserved:
    pytest tests/test_integration_staged.py -v -p no:randomly
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import threading
import time
from pathlib import Path

import pytest

from src.edf.adapters.gseb import GSEBAdapter
from src.edf.core.downloader import DownloadPipeline
from src.edf.manifests.manager import ManifestManager
from src.edf.models.data import DownloadDescriptor, RunSummary
from src.edf.storage.manager import StorageManager
from src.edf.utils.hashing import sha256_file
from src.edf.utils.pdf import validate_pdf_header, validate_pdf_size


# ---------------------------------------------------------------------------
# Session fixture: build a real PDF, serve it, run the pipeline ONCE.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def integ_session(tmp_path_factory):
    """One shared end-to-end run; stages assert slices of its output."""
    # Build a real, valid PDF (>10 KB to clear the min-size gate).
    pdf = b"%PDF-1.4\n"
    pdf += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    pdf += b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    pdf += b"% comment padding " + (b"x" * 11000) + b"\n"
    pdf += b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"

    fname = "std9_english_sample.pdf"
    www = tmp_path_factory.mktemp("www")
    (www / fname).write_bytes(pdf)

    # Serve the file via a local HTTP server on a free port.
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(www)
    )
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    url = f"http://127.0.0.1:{port}/{fname}"

    # Set up the real stack.
    content_root = tmp_path_factory.mktemp("content")
    storage = StorageManager(content_root=content_root)
    manifest = ManifestManager(storage_manager=storage)
    manifest.load_existing()
    config = {
        "gseb": {"textbooks": [{
            "std": "09", "subject": "social-science", "medium": "english",
            "language": "en", "url": url, "filename": fname,
            "title": "GSEB Std 9 Social Science (Sample)",
        }]},
        "download": {"max_retries": 1, "timeout_seconds": 10, "chunk_size": 8192},
        "validation": {"min_size_bytes": 1024},
    }
    adapter = GSEBAdapter(config=config)
    pipeline = DownloadPipeline(
        storage_manager=storage, manifest_manager=manifest, config=config
    )
    descriptors = adapter.get_descriptors()
    summary = pipeline.run(descriptors=descriptors, run_id="integ_run_001")
    target = storage.resolve_path("GSEB", "09", "social-science", "english", fname)

    session = {
        "pdf": pdf, "fname": fname, "url": url,
        "adapter": adapter, "pipeline": pipeline,
        "storage": storage, "manifest": manifest,
        "descriptors": descriptors, "summary": summary, "target": target,
    }
    yield session
    httpd.shutdown()
    httpd.server_close()


# ---------------------------------------------------------------------------
# Stage 3.1 — Adapter initialization
# ---------------------------------------------------------------------------

class TestStage31AdapterInit:
    def test_adapter_loads_gseb_section(self, integ_session):
        a = integ_session["adapter"]
        assert a.board_name == "GSEB"
        assert len(a._textbooks) == 1

    def test_download_config_loaded(self, integ_session):
        assert integ_session["adapter"]._download_config["timeout_seconds"] == 10


# ---------------------------------------------------------------------------
# Stage 3.2 — Descriptor generation
# ---------------------------------------------------------------------------

class TestStage32Descriptors:
    def test_one_descriptor_produced(self, integ_session):
        assert len(integ_session["descriptors"]) == 1

    def test_descriptor_fields(self, integ_session):
        d = integ_session["descriptors"][0]
        assert isinstance(d, DownloadDescriptor)
        assert d.board == "GSEB"
        assert d.std == "09"
        assert d.subject == "social-science"
        assert d.medium == "english"
        assert d.language == "en"
        assert d.filename == integ_session["fname"]


# ---------------------------------------------------------------------------
# Stage 3.3 — DownloadPipeline execution
# ---------------------------------------------------------------------------

class TestStage33Pipeline:
    def test_summary_counts(self, integ_session):
        s = integ_session["summary"]
        assert s.attempted == 1
        assert s.succeeded == 1
        assert s.skipped == 0
        assert s.failed == 0

    def test_exit_code_zero(self, integ_session):
        assert integ_session["summary"].exit_code == 0


# ---------------------------------------------------------------------------
# Stage 3.4 — HTTP download verification
# ---------------------------------------------------------------------------

class TestStage34HttpDownload:
    def test_file_on_disk(self, integ_session):
        assert integ_session["target"].exists()
        assert integ_session["target"].is_file()

    def test_bytes_match_source(self, integ_session):
        assert integ_session["target"].read_bytes() == integ_session["pdf"]


# ---------------------------------------------------------------------------
# Stage 3.5 — PDF validation
# ---------------------------------------------------------------------------

class TestStage35PdfValidation:
    def test_header_valid(self, integ_session):
        assert validate_pdf_header(integ_session["target"]) is True

    def test_size_valid(self, integ_session):
        assert validate_pdf_size(integ_session["target"], min_bytes=1024) is True


# ---------------------------------------------------------------------------
# Stage 3.6 — SHA-256 registration
# ---------------------------------------------------------------------------

class TestStage36Sha256Registration:
    def test_checksum_registered(self, integ_session):
        sha = sha256_file(integ_session["target"])
        assert integ_session["storage"].is_duplicate(sha) is not None

    def test_registry_path_contains_target(self, integ_session):
        sha = sha256_file(integ_session["target"])
        paths = integ_session["storage"].is_duplicate(sha)
        assert any(str(integ_session["target"]) in p for p in paths)


# ---------------------------------------------------------------------------
# Stage 3.7 — StorageManager verification
# ---------------------------------------------------------------------------

class TestStage37StorageManager:
    def test_file_exists(self, integ_session):
        assert integ_session["storage"].file_exists(integ_session["target"])

    def test_get_checksum_matches(self, integ_session):
        sha = sha256_file(integ_session["target"])
        assert integ_session["storage"].get_checksum(integ_session["target"]) == sha

    def test_relative_path(self, integ_session):
        rel = integ_session["storage"].to_relative_path(integ_session["target"])
        assert rel == "GSEB/" + integ_session["fname"]


# ---------------------------------------------------------------------------
# Stage 3.8 — ManifestManager verification
# ---------------------------------------------------------------------------

class TestStage38ManifestManager:
    def test_entry_registered(self, integ_session):
        rel = integ_session["storage"].to_relative_path(integ_session["target"])
        entry = integ_session["manifest"].get_entry(rel)
        assert entry is not None

    def test_entry_metadata(self, integ_session):
        rel = integ_session["storage"].to_relative_path(integ_session["target"])
        e = integ_session["manifest"].get_entry(rel)
        sha = sha256_file(integ_session["target"])
        assert e.board == "GSEB"
        assert e.std == "09"
        assert e.sha256 == sha
        assert e.size_bytes == len(integ_session["pdf"])
        assert e.source_url == integ_session["url"]


# ---------------------------------------------------------------------------
# Stage 3.9 — RunSummary verification
# ---------------------------------------------------------------------------

class TestStage39RunSummary:
    def test_summary_is_runsummary(self, integ_session):
        assert isinstance(integ_session["summary"], RunSummary)

    def test_run_id(self, integ_session):
        assert integ_session["summary"].run_id == "integ_run_001"

    def test_board_summary(self, integ_session):
        bs = integ_session["summary"].board_summaries["GSEB"]
        assert bs["attempted"] == 1
        assert bs["succeeded"] == 1
        assert bs["failed"] == 0
