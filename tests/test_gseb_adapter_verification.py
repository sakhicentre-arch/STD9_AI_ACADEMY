"""
EDF-L1 Phase 5 — GSEB Adapter Behavioural Verification Suite.

This module verifies the public behaviour of ``GSEBAdapter`` against the
contract defined by ``BaseAdapter`` and the data models in
``src.edf.models.data``.

Scope:
    - Configuration loading (gseb.textbooks, download section)
    - Required field validation
    - Missing field detection
    - Invalid URL detection
    - Descriptor generation (board / medium / subject / std / language / filename)
    - Duplicate descriptor handling (same path)
    - Pre-flight validation (warnings vs fatal errors)
    - Edge cases (empty config, malformed config, unknown fields, multiple/large lists)
    - Integration: real GSEB source-registry URL (optional, network-gated)

Rules:
    - Network is NEVER silently required. Any test that would touch the
      network is guarded so it skips cleanly when offline.
    - No production code is modified by this suite.
"""

from __future__ import annotations

import inspect
import socket
from typing import List
from unittest import mock

import pytest

from src.edf.adapters.base import BaseAdapter
from src.edf.adapters.gseb import GSEBAdapter
from src.edf.models.data import (
    DownloadDescriptor,
    PreflightIssue,
    PreflightSeverity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A textbook entry that satisfies every required field.
def _good_textbook(**overrides) -> dict:
    base = {
        "std": "09",
        "subject": "social-science",
        "medium": "english",
        "language": "en",
        "url": "https://example.org/std9_sst_en.pdf",
        "filename": "std9_english_social-science.pdf",
    }
    base.update(overrides)
    return base


def _config(textbooks=None, download=None, **extra) -> dict:
    """Build a full config dict rooted at the top level (not 'gseb')."""
    cfg = {
        "gseb": {"textbooks": textbooks if textbooks is not None else []},
    }
    if download is not None:
        cfg["download"] = download
    cfg.update(extra)
    return cfg


def _has_internet(host="8.8.8.8", port=53, timeout=2) -> bool:
    """Cheap connectivity probe (DNS server)."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except OSError:
        return False


# Official GSEB Tier-3 sample PDF already listed in the project's
# CONTENT/METADATA/SOURCE_REGISTRY.md (row #19). Used for live integration
# tests only — never invented.
OFFICIAL_SAMPLE_URL = (
    "https://cdn1.byjus.com/wp-content/uploads/2020/01/"
    "GSEB-Board-Class-9-Social-Science-Textbook-in-English.pdf"
)


def _issues_of(adapter: GSEBAdapter) -> List[PreflightIssue]:
    return adapter.pre_flight()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def adapter_factory():
    """Return a function that builds a GSEBAdapter from a config dict."""
    def _make(textbooks=None, download=None, **extra):
        return GSEBAdapter(config=_config(textbooks, download, **extra))
    return _make


@pytest.fixture
def good_adapter(adapter_factory):
    """Adapter with one fully-valid textbook entry."""
    return adapter_factory(textbooks=[_good_textbook()])


# ---------------------------------------------------------------------------
# 1. Configuration loading
# ---------------------------------------------------------------------------

class TestConfigLoading:
    def test_reads_gseb_textbooks_section(self, adapter_factory):
        adapter = adapter_factory(textbooks=[_good_textbook()])
        assert len(adapter._textbooks) == 1

    def test_missing_gseb_section_defaults_to_empty(self):
        adapter = GSEBAdapter(config={})
        assert adapter._textbooks == []

    def test_missing_textbooks_key_defaults_to_empty(self):
        adapter = GSEBAdapter(config={"gseb": {}})
        assert adapter._textbooks == []

    def test_download_section_read_for_timeout(self, adapter_factory):
        adapter = adapter_factory(
            textbooks=[_good_textbook()],
            download={"timeout_seconds": 7},
        )
        assert adapter._download_config.get("timeout_seconds") == 7

    def test_missing_download_section_defaults_empty(self, good_adapter):
        assert good_adapter._download_config == {}


# ---------------------------------------------------------------------------
# 2. Required configuration validation
# ---------------------------------------------------------------------------

class TestRequiredFieldValidation:
    REQUIRED = ["std", "subject", "medium", "language", "url", "filename"]

    @pytest.mark.parametrize("missing_field", REQUIRED)
    def test_missing_required_field_emits_error(self, adapter_factory, missing_field):
        tb = _good_textbook()
        tb.pop(missing_field)
        adapter = adapter_factory(textbooks=[tb])

        issues = [i for i in _issues_of(adapter)
                  if i.code == "GSEB_MISSING_FIELDS"]
        assert len(issues) == 1
        assert missing_field in issues[0].context["missing_fields"]
        assert issues[0].severity == PreflightSeverity.ERROR

    @pytest.mark.parametrize("missing_field", REQUIRED)
    def test_missing_field_skipped_in_descriptors(
        self, adapter_factory, missing_field
    ):
        tb = _good_textbook()
        tb.pop(missing_field)
        adapter = adapter_factory(textbooks=[tb])
        assert adapter.get_descriptors() == []

    def test_falsy_empty_string_treated_as_missing(self, adapter_factory):
        tb = _good_textbook(url="")
        adapter = adapter_factory(textbooks=[tb])
        issues = [i for i in _issues_of(adapter)
                  if i.code == "GSEB_MISSING_FIELDS"]
        assert len(issues) == 1
        assert "url" in issues[0].context["missing_fields"]

    def test_all_fields_present_no_missing_error(self, good_adapter):
        issues = [i for i in _issues_of(good_adapter)
                  if i.code == "GSEB_MISSING_FIELDS"]
        assert issues == []


# ---------------------------------------------------------------------------
# 3. Invalid URL detection
# ---------------------------------------------------------------------------

class TestUrlValidation:
    # NOTE: "" (empty string) is intentionally NOT listed here. An empty URL
    # is a *missing field* and is classified as GSEB_MISSING_FIELDS, never
    # reaching the scheme check (see TestRequiredFieldValidation).
    @pytest.mark.parametrize("bad_url", [
        "ftp://example.org/x.pdf",
        "file:///etc/passwd",
        "example.org/x.pdf",          # missing scheme
        "//example.org/x.pdf",        # protocol-relative
        "javascript:alert(1)",
    ])
    def test_invalid_scheme_emits_error(self, adapter_factory, bad_url):
        adapter = adapter_factory(textbooks=[_good_textbook(url=bad_url)])
        issues = [i for i in _issues_of(adapter)
                  if i.code == "GSEB_INVALID_URL"]
        assert len(issues) == 1
        assert issues[0].severity == PreflightSeverity.ERROR

    @pytest.mark.parametrize("good_url", [
        "http://example.org/x.pdf",
        "https://example.org/x.pdf",
        "https://gsstb.gujarat.gov.in/path/book.pdf",
    ])
    def test_valid_scheme_no_invalid_error(
        self, adapter_factory, good_url, monkeypatch
    ):
        # Stub HEAD so URL-format check is isolated from network.
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: {"status_code": 200, "headers": {}},
        )
        adapter = adapter_factory(textbooks=[_good_textbook(url=good_url)])
        issues = [i for i in _issues_of(adapter)
                  if i.code == "GSEB_INVALID_URL"]
        assert issues == []


# ---------------------------------------------------------------------------
# 4. URL normalization (resolve_url)
# ---------------------------------------------------------------------------

class TestUrlNormalization:
    def test_resolve_url_returns_descriptor_url_unchanged(self, good_adapter):
        desc = good_adapter.get_descriptors()[0]
        assert good_adapter.resolve_url(desc) == desc.url

    def test_resolve_url_with_query_and_fragment(self, adapter_factory):
        url = "https://example.org/x.pdf?v=2&lang=en#page=5"
        adapter = adapter_factory(textbooks=[_good_textbook(url=url)])
        desc = adapter.get_descriptors()[0]
        assert adapter.resolve_url(desc) == url


# ---------------------------------------------------------------------------
# 5. Descriptor generation
# ---------------------------------------------------------------------------

class TestDescriptorGeneration:
    def test_descriptor_count_matches_valid_entries(self, adapter_factory):
        adapter = adapter_factory(textbooks=[
            _good_textbook(),
            _good_textbook(filename="b.pdf"),
        ])
        assert len(adapter.get_descriptors()) == 2

    def test_descriptor_is_download_descriptor_instance(self, good_adapter):
        desc = good_adapter.get_descriptors()[0]
        assert isinstance(desc, DownloadDescriptor)

    def test_descriptor_board_is_gseb(self, good_adapter):
        assert good_adapter.get_descriptors()[0].board == "GSEB"

    def test_descriptor_std(self, adapter_factory):
        adapter = adapter_factory(textbooks=[_good_textbook(std="10")])
        assert adapter.get_descriptors()[0].std == "10"

    def test_descriptor_subject(self, adapter_factory):
        adapter = adapter_factory(textbooks=[_good_textbook(subject="maths")])
        assert adapter.get_descriptors()[0].subject == "maths"

    def test_descriptor_medium(self, adapter_factory):
        adapter = adapter_factory(textbooks=[_good_textbook(medium="gujarati")])
        assert adapter.get_descriptors()[0].medium == "gujarati"

    def test_descriptor_language(self, adapter_factory):
        adapter = adapter_factory(textbooks=[_good_textbook(language="gu")])
        assert adapter.get_descriptors()[0].language == "gu"

    def test_descriptor_filename(self, adapter_factory):
        adapter = adapter_factory(textbooks=[_good_textbook(filename="my.pdf")])
        assert adapter.get_descriptors()[0].filename == "my.pdf"

    def test_descriptor_url(self, adapter_factory):
        url = "https://h.example.org/book.pdf"
        adapter = adapter_factory(textbooks=[_good_textbook(url=url)])
        assert adapter.get_descriptors()[0].url == url

    def test_descriptor_std_is_stringified(self, adapter_factory):
        # Integer std must be coerced to str (descriptor contract).
        adapter = adapter_factory(textbooks=[_good_textbook(std=9)])
        desc = adapter.get_descriptors()[0]
        assert desc.std == "9"
        assert isinstance(desc.std, str)

    def test_descriptor_metadata_has_required_keys(self, good_adapter):
        meta = good_adapter.get_descriptors()[0].metadata
        for key in ("adapter", "title", "publisher", "academic_year"):
            assert key in meta
        assert meta["adapter"] == "GSEB"

    def test_descriptor_publisher_defaults_to_gseb(self, good_adapter):
        assert good_adapter.get_descriptors()[0].metadata["publisher"] == "GSEB"

    def test_descriptor_optional_sha256_and_size(self, adapter_factory):
        adapter = adapter_factory(textbooks=[_good_textbook(
            expected_sha256="a" * 64,
            expected_size_bytes=12345,
        )])
        desc = adapter.get_descriptors()[0]
        assert desc.expected_sha256 == "a" * 64
        assert desc.expected_size_bytes == 12345

    def test_descriptor_optional_fields_default_none(self, good_adapter):
        desc = good_adapter.get_descriptors()[0]
        assert desc.expected_sha256 is None
        assert desc.expected_size_bytes is None


# ---------------------------------------------------------------------------
# 6. Duplicate descriptor handling
# ---------------------------------------------------------------------------

class TestDuplicateDescriptorHandling:
    def test_two_entries_same_fields_produce_two_descriptors(
        self, adapter_factory
    ):
        # Adapter itself does not dedup — that is the StorageManager's job.
        adapter = adapter_factory(textbooks=[
            _good_textbook(),
            _good_textbook(),
        ])
        descs = adapter.get_descriptors()
        assert len(descs) == 2

    def test_get_descriptors_idempotent_per_call(self, good_adapter):
        first = good_adapter.get_descriptors()
        second = good_adapter.get_descriptors()
        assert len(first) == len(second) == 1
        assert first[0].filename == second[0].filename


# ---------------------------------------------------------------------------
# 7. Pre-flight validation
# ---------------------------------------------------------------------------

class TestPreflight:
    def test_empty_textbooks_returns_single_warning(self, adapter_factory):
        adapter = adapter_factory(textbooks=[])
        issues = adapter.pre_flight()
        assert len(issues) == 1
        assert issues[0].code == "GSEB_NO_TEXTBOOKS"
        assert issues[0].severity == PreflightSeverity.WARNING

    def test_preflight_returns_preflightissue_list(self, good_adapter, monkeypatch):
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: {"status_code": 200, "headers": {}},
        )
        issues = good_adapter.pre_flight()
        assert isinstance(issues, list)
        assert all(isinstance(i, PreflightIssue) for i in issues)

    def test_valid_entry_with_reachable_url_no_errors(
        self, good_adapter, monkeypatch
    ):
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: {"status_code": 200, "headers": {}},
        )
        issues = good_adapter.pre_flight()
        assert all(i.severity != PreflightSeverity.ERROR for i in issues)

    def test_url_unreachable_emits_warning_not_error(
        self, good_adapter, monkeypatch
    ):
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: None,
        )
        issues = good_adapter.pre_flight()
        unreachable = [i for i in issues if i.code == "GSEB_URL_UNREACHABLE"]
        assert len(unreachable) == 1
        assert unreachable[0].severity == PreflightSeverity.WARNING

    def test_http_error_status_emits_warning(self, good_adapter, monkeypatch):
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: {"status_code": 503, "headers": {}},
        )
        issues = good_adapter.pre_flight()
        http_err = [i for i in issues if i.code == "GSEB_URL_HTTP_ERROR"]
        assert len(http_err) == 1
        assert http_err[0].context["status_code"] == 503

    def test_missing_fields_aborts_url_check_for_that_entry(
        self, adapter_factory, monkeypatch
    ):
        called = {"count": 0}

        def _head(url, timeout=30):
            called["count"] += 1
            return {"status_code": 200, "headers": {}}

        monkeypatch.setattr("src.edf.adapters.gseb.head_request", _head)
        adapter = adapter_factory(textbooks=[
            _good_textbook(subject=""),  # missing field -> skip url check
        ])
        adapter.pre_flight()
        assert called["count"] == 0

    def test_invalid_url_aborts_reachability_check(
        self, adapter_factory, monkeypatch
    ):
        called = {"count": 0}

        def _head(url, timeout=30):
            called["count"] += 1
            return {"status_code": 200, "headers": {}}

        monkeypatch.setattr("src.edf.adapters.gseb.head_request", _head)
        adapter = adapter_factory(textbooks=[
            _good_textbook(url="ftp://x/y.pdf"),
        ])
        adapter.pre_flight()
        assert called["count"] == 0


# ---------------------------------------------------------------------------
# 8. BaseAdapter contract conformance
# ---------------------------------------------------------------------------

class TestBaseAdapterConformance:
    def test_is_subclass_of_baseadapter(self):
        assert issubclass(GSEBAdapter, BaseAdapter)

    def test_board_name_is_gseb(self):
        adapter = GSEBAdapter(config={})
        assert adapter.board_name == "GSEB"

    def test_implements_all_abstract_methods(self):
        for name in ("board_name", "pre_flight", "get_descriptors", "resolve_url"):
            attr = getattr(GSEBAdapter, name, None)
            assert attr is not None, f"Missing {name}"
            # Must be concrete (not still abstract).
            assert not getattr(attr, "__isabstractmethod__", False)

    def test_constructor_signature_accepts_config_and_http_client(self):
        sig = inspect.signature(GSEBAdapter.__init__)
        params = list(sig.parameters)
        assert "config" in params
        assert "http_client" in params

    def test_instance_repr_works(self):
        # Should not raise.
        assert isinstance(repr(GSEBAdapter(config={})), str)


# ---------------------------------------------------------------------------
# 9. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_config(self):
        adapter = GSEBAdapter(config={})
        assert adapter.board_name == "GSEB"
        assert adapter.get_descriptors() == []
        issues = adapter.pre_flight()
        assert len(issues) == 1
        assert issues[0].code == "GSEB_NO_TEXTBOOKS"

    def test_malformed_textbooks_not_a_list(self, adapter_factory):
        # If textbooks is a dict instead of a list, iterating is undefined.
        adapter = adapter_factory(textbooks={"std": "09"})
        # Iterating a dict yields its keys (strings) — these have no .get().
        with pytest.raises(AttributeError):
            adapter.pre_flight()

    def test_textbook_entry_with_unknown_fields_ignored(self, adapter_factory):
        adapter = adapter_factory(textbooks=[
            _good_textbook(unknown_field="ignored", tier=1, notes="x"),
        ])
        descs = adapter.get_descriptors()
        assert len(descs) == 1
        # Unknown fields must not leak into descriptor attributes.
        assert not hasattr(descs[0], "unknown_field")

    def test_unknown_top_level_config_keys_ignored(self):
        adapter = GSEBAdapter(config={
            "gseb": {"textbooks": [_good_textbook()]},
            "ncert": {"textbooks": []},
            "weird_top": True,
        })
        assert len(adapter.get_descriptors()) == 1

    def test_multiple_textbooks_mixed_validity(self, adapter_factory, monkeypatch):
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: {"status_code": 200, "headers": {}},
        )
        adapter = adapter_factory(textbooks=[
            _good_textbook(filename="a.pdf"),
            _good_textbook(filename="b.pdf", subject=""),   # invalid
            _good_textbook(filename="c.pdf"),               # valid
        ])
        descs = adapter.get_descriptors()
        filenames = {d.filename for d in descs}
        assert filenames == {"a.pdf", "c.pdf"}

    def test_large_descriptor_list(self, adapter_factory):
        n = 200
        books = [_good_textbook(filename=f"book_{i}.pdf") for i in range(n)]
        adapter = adapter_factory(textbooks=books)
        descs = adapter.get_descriptors()
        assert len(descs) == n

    def test_unicode_subject_and_filename(self, adapter_factory):
        adapter = adapter_factory(textbooks=[
            _good_textbook(subject="ગુજરાતી", filename="std9_ગુજરાતી.pdf"),
        ])
        desc = adapter.get_descriptors()[0]
        assert desc.subject == "ગુજરાતી"
        assert desc.filename == "std9_ગુજરાતી.pdf"


# ---------------------------------------------------------------------------
# 10. Recoverable warnings vs fatal failures
# ---------------------------------------------------------------------------

class TestRecoverableVsFatal:
    def test_unreachable_url_does_not_block_descriptor(self, adapter_factory, monkeypatch):
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: None,
        )
        adapter = adapter_factory(textbooks=[_good_textbook()])
        # Even with unreachable URL, the descriptor is still generated.
        assert len(adapter.get_descriptors()) == 1
        issues = adapter.pre_flight()
        assert any(i.code == "GSEB_URL_UNREACHABLE" for i in issues)
        # No ERROR-level issue.
        assert not any(i.severity == PreflightSeverity.ERROR for i in issues)

    def test_missing_field_is_fatal_for_that_entry(self, adapter_factory):
        adapter = adapter_factory(textbooks=[
            _good_textbook(filename="ok.pdf"),
            _good_textbook(filename="bad.pdf", url=""),  # ERROR-level
        ])
        issues = adapter.pre_flight()
        errors = [i for i in issues if i.severity == PreflightSeverity.ERROR]
        assert len(errors) == 1
        assert errors[0].code == "GSEB_MISSING_FIELDS"


# ---------------------------------------------------------------------------
# 11. Real-world sample configuration (offline-mocked)
# ---------------------------------------------------------------------------

class TestRealWorldSampleConfig:
    def test_real_gseb_sample_config_yields_descriptor(self, adapter_factory, monkeypatch):
        # Sample from the project's source registry (row #19).
        monkeypatch.setattr(
            "src.edf.adapters.gseb.head_request",
            lambda url, timeout=30: {"status_code": 200, "headers": {}},
        )
        adapter = adapter_factory(textbooks=[{
            "std": "09",
            "subject": "social-science",
            "medium": "english",
            "language": "en",
            "url": OFFICIAL_SAMPLE_URL,
            "filename": "std9_english_social-science.pdf",
            "title": "GSEB Class 9 Social Science (English)",
            "publisher": "GSSTB",
            "academic_year": "2025-26",
        }])
        descs = adapter.get_descriptors()
        assert len(descs) == 1
        assert descs[0].url == OFFICIAL_SAMPLE_URL
        issues = adapter.pre_flight()
        assert not any(i.severity == PreflightSeverity.ERROR for i in issues)


# ---------------------------------------------------------------------------
# 12. Integration: live GSEB source-registry URL (network-gated)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _has_internet(),
    reason="No internet connectivity — skipping live integration tests.",
)
class TestLiveIntegration:
    def test_live_sample_url_reachable_and_is_pdf(self):
        from src.edf.utils.http import head_request
        result = head_request(OFFICIAL_SAMPLE_URL, timeout=20)
        assert result is not None, "HEAD request returned no response"
        assert result["status_code"] == 200
        ctype = result["headers"].get("Content-Type", "")
        assert "pdf" in ctype.lower(), f"Unexpected Content-Type: {ctype}"

    def test_live_adapter_preflight_on_real_url(self, adapter_factory):
        adapter = adapter_factory(textbooks=[{
            "std": "09",
            "subject": "social-science",
            "medium": "english",
            "language": "en",
            "url": OFFICIAL_SAMPLE_URL,
            "filename": "std9_english_social-science.pdf",
        }])
        issues = adapter.pre_flight()
        # No ERROR-level issues on a reachable 200 URL.
        assert not any(i.severity == PreflightSeverity.ERROR for i in issues)
