# EDF-L1 — Education Download Framework, Level 1

Automated PDF acquisition and management for educational textbooks (GSEB, NCERT).

> **Status:** Phase 5 complete — ✅ **Production ready** for the GSEB source.
> Full suite: **174 tests passing**. See
> [`VERIFICATION_REPORT_PHASE5.md`](./VERIFICATION_REPORT_PHASE5.md) and
> [`PHASE5_BASELINE.md`](./PHASE5_BASELINE.md).

---

## Table of Contents

- [Current Architecture](#current-architecture)
- [Installation](#installation)
- [Running Tests](#running-tests)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [Project Status](#project-status)
- [Roadmap](#roadmap)
- [License](#license)

---

## Current Architecture

EDF-L1 is a **board-agnostic** download framework. Each board (GSEB, NCERT, …)
is implemented as a `BaseAdapter`; a shared pipeline handles download, validation,
storage, and manifest registration.

```
                 ┌──────────────────────────────────────────────┐
   config.yaml → │  Core (config loader)                        │
                 └───────────────┬──────────────────────────────┘
                                 │
                ┌────────────────┴───────────────┐
                ▼                                ▼
   ┌─────────────────────┐         ┌─────────────────────────┐
   │  adapters/          │         │  models/                │
   │   ├─ base.py        │←contract│   DownloadDescriptor    │
   │   ├─ gseb.py (✅)   │         │   RunSummary            │
   │   ├─ ncert.py (✅)   │         │   PreflightIssue        │
   │   └─ registry.py (✅) │         │   ManifestEntry          │
   └──────────┬──────────┘         └─────────────────────────┘
              │ descriptors
              ▼
   ┌──────────────────────────────────────────────────────────┐
   │  core/                                                   │
   │   ├─ pipeline.py        — board-agnostic coordination    │
   │   └─ downloader.py      — DownloadPipeline (per-board)   │
   └──────────┬──────────────────────────────────┬────────────┘
              ▼                                   ▼
   ┌─────────────────────┐            ┌─────────────────────────┐
   │  storage/manager.py │            │  manifests/manager.py   │
   │  atomic write,      │← checksums │  entry register/merge   │
   │  SHA-256 registry,  │  ─────────→│                         │
   │  dedup, paths       │            │  ManifestEntry          │
   └─────────────────────┘            └─────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────────────────────────────┐
   │  utils/  hashing.py · http.py · pdf.py                   │
   │  logging/logger.py                                       │
   └──────────────────────────────────────────────────────────┘
```

**Key design properties**

- **Board-agnostic** — new boards implement `BaseAdapter` (`board_name`,
  `pre_flight`, `get_descriptors`, `resolve_url`).
- **Pre-flight first** — adapters classify issues as `WARNING` (recoverable) or
  `ERROR` (fatal for that entry) *before* any download.
- **Content-addressed storage** — SHA-256 registry powers dedup; atomic writes
  with temp-file placement and path-traversal sanitization.
- **Manifest-tracked** — every stored file is registered with board/std/subject/
  medium/source_url/sha256/size metadata.

### Implemented Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `adapters/base.py` | Adapter contract | ✅ Stable |
| `adapters/gseb.py` | GSEB source adapter | ✅ Verified |
| `core/config.py` | Configuration loading | ✅ Stable |
| `core/pipeline.py` | Run coordination | ✅ Verified |
| `core/downloader.py` | DownloadPipeline | ✅ Verified |
| `storage/manager.py` | Filesystem + checksum registry | ✅ Verified |
| `manifests/manager.py` | Manifest register/merge | ✅ Verified |
| `models/data.py` | Models & interfaces | ✅ Stable |
| `utils/{hashing,http,pdf}.py` | Helpers | ✅ Stable |
| `logging/logger.py` | Structured logging | ✅ Stable |

---

## Installation

Requirements: **Python 3.12+**.

```bash
# 1. Clone
git clone <repo-url> STD9_AI_ACADEMY
cd STD9_AI_ACADEMY

# 2. Create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# POSIX:    source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and edit configuration
cp config/config.yaml.example config.yaml
#   edit: general.content_root, gseb.textbooks

# 5. Smoke-check the bootstrap
python main.py
```

---

## Running Tests

The full suite is **174 tests** and runs in ~3.5 s.

```bash
# Full suite (behavioural + integration + regression)
python -m pytest tests

# Verbose, per-test
python -m pytest tests -v

# The staged end-to-end integration run (9 stages, ordered)
python -m pytest tests/test_integration_staged.py -v -p no:randomly

# GSEB adapter behavioural suite (69 tests)
python -m pytest tests/test_gseb_adapter_verification.py -v

# One-shot verification with a summary line
# (prints total / passed / failed / duration / exit code; non-zero on failure)
python scripts/verify_all.py
python scripts/verify_all.py --verbose
```

`scripts/verify_all.py` returns a **non-zero exit code on any failure**, so it is
safe to wire into CI / pre-merge gates.

### Test Inventory

| File | Scope | Tests |
|------|-------|-------|
| `tests/test_gseb_adapter_verification.py` | GSEBAdapter behaviour (12 sections) | 69 |
| `tests/test_integration_staged.py` | 9-stage end-to-end (stages 3.1–3.9) | 20 |
| `tests/test_storage_manager_verification.py` | Atomicity, checksums, paths | 85 |
| `tests/test_manifest_manager_verification.py` | Manifest registration/metadata | — |
| **Total** | | **174 (all passing)** |

> Two live integration tests are **network-gated** and skip cleanly when offline.

---

## Configuration

Copy `config/config.yaml.example` to `config.yaml` and edit:

- `general.content_root` — Path to the `CONTENT` directory.
- `gseb.textbooks` — GSEB textbook entries (`std`, `subject`, `medium`,
  `language`, `url`, `filename`, optional `title`/`publisher`/`academic_year`).
- `download` — `max_retries`, `timeout_seconds`, `chunk_size`.
- `validation` — `min_size_bytes`.

---

## CLI Usage

```bash
python main.py                  # Run full pipeline
python main.py --dry-run        # Simulate without downloading
python main.py --board GSEB     # Run for a single board
python main.py --verify-only    # Re-validate existing files
```

---

## Project Status

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | ✅ Complete | Project skeleton, models, logging, CLI bootstrap |
| 2 | ✅ Complete | GSEB adapter, BaseAdapter contract, pre-flight |
| 3 | ✅ Complete | DownloadPipeline, validation, HTTP fetch |
| 4 | ✅ Complete | StorageManager, ManifestManager, checksum registry |
| 5 | ✅ **Complete** | Hardening, documentation, full verification (174 tests) |
| 6 | ⬜ Pending | NCERT adapter, deep PDF validation, concurrency |

**Phase 5 deliverables**

- `VERIFICATION_REPORT_PHASE5.md` — full verification report.
- `PHASE5_BASELINE.md` — frozen baseline (APIs, modules, risks, Phase 6 prereqs).
- `scripts/verify_all.py` — CI-friendly verification runner.
- Updated `README.md` — architecture, install, tests, status, roadmap.

---

## Roadmap

### ✅ Done (Phases 1–5)

- Skeleton, models, structured logging, CLI bootstrap.
- Board-agnostic `BaseAdapter`; GSEB adapter with pre-flight severity model.
- `DownloadPipeline` with HTTP fetch, retry config, validation hooks.
- `StorageManager`: atomic writes, SHA-256 registry, dedup, path sanitization.
- `ManifestManager`: entry registration, metadata, merge.
- Full verification: 174 tests passing, live integration confirmed.

### ⬜ Phase 6 (next)

1. **NCERT adapter** — implement against `BaseAdapter`; master-list validation.
2. **Deep PDF validation** — structural / object-level checks beyond header+size.
3. **Multi-textbook concurrency & stress** — parallel fetch, backpressure.
4. **Retry/backoff telemetry** — assert retry-path behaviour.
5. **CLI flag coverage** — automated tests for `--dry-run`, `--board`, `--verify-only`.
6. **CONTENT scanning & manifest-merge hardening.**

---

## License

MIT
