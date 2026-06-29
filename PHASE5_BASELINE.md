# Phase 5 Baseline

| Field | Value |
|-------|-------|
| Phase | 5 — Hardening, Documentation, Verification |
| Baseline Date | 2026-06-29 |
| Status | ✅ Complete — Production Ready |
| Commit Hash (placeholder) | `ff908f8` |
| Version Tag (placeholder) | `v0.5.0-phase5` |

This document captures the **frozen Phase 5 baseline**: directory structure, public
APIs, implemented modules, test inventory, deferred work, risks, and the
prerequisites for Phase 6.

---

## 1. Directory Structure

```
STD9_AI_ACADEMY/
├── main.py                       # CLI entry point
├── README.md                     # Project overview (updated for Phase 5)
├── VERIFICATION_REPORT_PHASE5.md # Phase 5 verification report
├── PHASE5_BASELINE.md            # This file
├── config/
│   └── config.yaml.example       # Example configuration
├── scripts/
│   └── verify_all.py             # Full-suite verification runner (Phase 5)
├── src/
│   └── edf/
│       ├── __init__.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py           # BaseAdapter abstract contract
│       │   └── gseb.py           # GSEBAdapter (verified)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py         # Configuration loading
│       │   ├── downloader.py     # DownloadPipeline orchestrator
│       │   └── pipeline.py       # Pipeline run/coordination
│       ├── logging/
│       │   ├── __init__.py
│       │   └── logger.py         # Structured logging
│       ├── manifests/
│       │   ├── __init__.py
│       │   └── manager.py        # ManifestManager (verified)
│       ├── models/
│       │   ├── __init__.py
│       │   └── data.py           # Data models & interfaces
│       ├── storage/
│       │   ├── __init__.py
│       │   └── manager.py        # StorageManager (verified)
│       └── utils/
│           ├── __init__.py
│           ├── hashing.py        # SHA-256 helpers
│           ├── http.py           # HEAD/GET HTTP client
│           └── pdf.py            # PDF header/size validation
└── tests/
    ├── __init__.py
    ├── unit/
    │   └── __init__.py
    ├── test_gseb_adapter_verification.py      # 69 tests
    ├── test_integration_staged.py             # 20 tests
    ├── test_storage_manager_verification.py
    └── test_manifest_manager_verification.py
```

---

## 2. Public APIs

### `src.edf.adapters.base.BaseAdapter` (abstract)
Defines the contract every source adapter must satisfy.

| Member | Kind | Notes |
|--------|------|-------|
| `board_name` | abstract property | Board identifier (e.g. `"GSEB"`) |
| `pre_flight() -> List[PreflightIssue]` | abstract method | Validation/warning report |
| `get_descriptors() -> List[DownloadDescriptor]` | abstract method | Build download targets |
| `resolve_url(descriptor) -> str` | abstract method | Resolve the final URL |
| `__init__(self, config, http_client=None)` | constructor | Shared signature |

### `src.edf.adapters.gseb.GSEBAdapter(BaseAdapter)`
Concrete GSEB implementation. Emits `GSEB_MISSING_FIELDS`, `GSEB_INVALID_URL`,
`GSEB_NO_TEXTBOOKS`, `GSEB_URL_UNREACHABLE`, `GSEB_URL_HTTP_ERROR` pre-flight issues.

### `src.edf.core.downloader.DownloadPipeline`
| Member | Kind | Notes |
|--------|------|-------|
| `__init__(storage_manager, manifest_manager, config)` | constructor | |
| `run(descriptors, run_id) -> RunSummary` | method | Orchestrates download/validate/register |

### `src.edf.storage.manager.StorageManager`
| Member | Kind | Notes |
|--------|------|-------|
| `resolve_path(board, std, subject, medium, filename)` | method | Absolute target path |
| `to_relative_path(path) -> str\|None` | method | Content-relative path |
| `file_exists(path) -> bool` | method | |
| `get_checksum(path) -> str` | method | Registered SHA-256 |
| `is_duplicate(sha) -> list\|None` | method | Duplicate detection |
| `atomic_write_bytes(...)` / `place(...)` / `cleanup_temp(...)` | methods | Atomic placement |
| `generate_metadata(path)` | method | Metadata dict |

### `src.edf.manifests.manager.ManifestManager`
| Member | Kind | Notes |
|--------|------|-------|
| `__init__(storage_manager)` | constructor | |
| `load_existing()` | method | Load manifest from disk |
| `get_entry(relative_path) -> ManifestEntry\|None` | method | Lookup |
| `register(...)` / `merge(...)` | methods | Mutation (per contract) |

### `src.edf.models.data`
Dataclasses/interfaces: `DownloadDescriptor`, `RunSummary`, `PreflightIssue`,
`PreflightSeverity`, `ManifestEntry`, and board-summary structures.

### `src.edf.utils`
- `hashing.sha256_file(path) -> str`
- `http.head_request(url, timeout) -> dict|None`
- `pdf.validate_pdf_header(path) -> bool`, `pdf.validate_pdf_size(path, min_bytes) -> bool`

---

## 3. Implemented Modules

| Module | Purpose | Phase 5 Status |
|--------|---------|----------------|
| `adapters/base.py` | Adapter contract | ✅ Stable |
| `adapters/gseb.py` | GSEB source adapter | ✅ Verified |
| `core/config.py` | Configuration loading | ✅ Stable |
| `core/pipeline.py` | Run coordination | ✅ Verified |
| `core/downloader.py` | DownloadPipeline | ✅ Verified |
| `storage/manager.py` | Filesystem + checksum registry | ✅ Verified |
| `manifests/manager.py` | Manifest register/merge | ✅ Verified |
| `models/data.py` | Models & interfaces | ✅ Stable |
| `utils/hashing.py` | SHA-256 | ✅ Stable |
| `utils/http.py` | HTTP client | ✅ Stable |
| `utils/pdf.py` | PDF validation | ✅ Stable |
| `logging/logger.py` | Structured logging | ✅ Stable |

---

## 4. Test Inventory

| File | Scope | Tests |
|------|-------|-------|
| `test_gseb_adapter_verification.py` | GSEBAdapter behaviour (12 sections) | 69 |
| `test_integration_staged.py` | 9-stage end-to-end (stages 3.1–3.9) | 20 |
| `test_storage_manager_verification.py` | Storage atomicity, checksums, paths | — |
| `test_manifest_manager_verification.py` | Manifest registration/metadata | — |
| **Total** | | **174 (all passing)** |

---

## 5. Deferred Work

- **NCERT adapter** — framework is board-agnostic; NCERT not yet implemented.
- **Deep PDF validation** — currently header + size only; structural/object
  validation deferred.
- **Concurrency / multi-textbook stress** — E2E currently single-textbook.
- **Retry/backoff telemetry assertions** — config loaded, path not asserted.
- **CLI flag hardening** — `--dry-run`, `--board`, `--verify-only` documented but
  not covered by automated verification in this baseline.
- **CONTENT scanning & manifest merge hardening** — out of Phase 5 scope.

---

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Third-party CDN URL drift (live tests) | Medium | Low | Network-gated; clean skip offline |
| Shallow PDF validation misses corrupt files | Medium | Medium | Phase 6 deep validation |
| Windows path edge cases | Low | Medium | Covered by `TestWindowsPathHandling` |
| Single-board scope limits reuse | High | Low | `BaseAdapter` ready for NCERT |
| Manifest concurrency not exercised | Low | Medium | Single-run E2E; deferred to Phase 6 |

---

## 7. Phase 6 Prerequisites

Phase 6 may begin once the following are confirmed:

1. ✅ Phase 5 verification complete — 174/174 tests passing.
2. ✅ GSEB adapter contract (`BaseAdapter`) stable and verified.
3. ✅ StorageManager, ManifestManager, DownloadPipeline verified end-to-end.
4. ✅ Release artifacts generated (`VERIFICATION_REPORT_PHASE5.md`,
   `PHASE5_BASELINE.md`, `scripts/verify_all.py`, updated `README.md`).
5. ⬜ Commit-hash and version-tag placeholders finalized at tagging time.
6. ⬜ (Recommended) Cut the `v0.5.0-phase5` tag before opening Phase 6 work.

**Phase 6 candidate scope:** NCERT adapter, deep PDF validation, multi-textbook
concurrency, retry/backoff telemetry, CLI flag coverage, and CONTENT/manifest
merge hardening.
