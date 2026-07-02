# EDF-L1 — Education Download Framework, Level 1

Automated PDF acquisition and management for educational textbooks (GSEB, NCERT).

> **Status:** Phase 7 complete — ✅ **Production ready** with CLI, ConfigLoader,
> and integration test suite. Full suite: **309 tests passing** across 10 modules.
> See [`docs/releases/RELEASE_v0.7.0.md`](./docs/releases/RELEASE_v0.7.0.md).

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
   ┌─────────────────────────┐    ┌─────────────────────────┐
   │  adapters/              │    │  models/                │
   │   ├─ base.py           │    │   DownloadDescriptor    │
   │   ├─ gseb.py (✅)      │    │   RunSummary            │
   │   ├─ ncert.py (✅)      │    │   PreflightIssue        │
   │   └─ registry.py (✅)   │    │   ManifestEntry          │
   │     ↑ AdapterRegistry  │    └─────────────────────────┘
   │     │ default_registry │
   │     │ board discovery  │
   └─────┼──────────────────┘
         │ enabled adapters
         ▼
   ┌──────────────────────────────────────────────────────────┐
   │  core/                                                   │
   │   ├─ pipeline.py        — board-agnostic orchestration    │
   │   └─ downloader.py      — DownloadPipeline (per-board)     │
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
| `adapters/ncert.py` | NCERT source adapter | ✅ Verified |
| `adapters/registry.py` | Board registry & discovery | ✅ Verified |
| `core/config.py` | Configuration loading | ✅ Stable |
| `core/pipeline.py` | Board-agnostic orchestration | ✅ Verified |
| `core/downloader.py` | DownloadPipeline (per-board) | ✅ Verified |
| `storage/manager.py` | Filesystem + checksum registry | ✅ Verified |
| `manifests/manager.py` | Manifest register/merge | ✅ Verified |
| `models/data.py` | Models & interfaces | ✅ Stable |
| `utils/{hashing,http,pdf}.py` | Helpers | ✅ Stable |
| `logging/logger.py` | Structured logging | ✅ Stable |

---

## Installation

Requirements: **Python 3.10+**.

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

The full suite is **230 tests** and runs in ~4.5 s.

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
| `tests/test_adapter_registry.py` | Registry behaviour, enabled-boards, backward compat | 39 |
| `tests/test_multiboard_aggregation.py` | Per-board DownloadPipeline summary | 7 |
| `tests/test_multiboard_integration.py` | Full multi-board orchestrator end-to-end | 1 |
| **Total** | | **230 (all passing)** |

> Two live integration tests are **network-gated** and skip cleanly when offline.

---

## Configuration

Copy `config/config.yaml.example` to `config.yaml` and edit:

- `general.content_root` — Path to the `CONTENT` directory.
- `boards` — Optional enable/disable flags per board (absent = all enabled).
- `gseb.textbooks` — GSEB textbook entries (`std`, `subject`, `medium`,
  `language`, `url`, `filename`, optional `title`/`publisher`/`academic_year`).
- `ncert.textbooks` — NCERT textbook entries (`code`, `std`, `subject`,
  `medium`, `language`, optional `part`/`url`/`filename`/`expected_sha256`).
- `download` — `max_retries`, `timeout_seconds`, `chunk_size`.
- `validation` — `min_size_bytes`.

---

## CLI Usage

After installation the `edf` entry point is available. Both invocations work:

```bash
edf                              # Run full pipeline (installed entry point)
edf --dry-run                    # Simulate without downloading
edf --board GSEB                 # Run for a single board
edf --verify-only                # Re-validate existing files
edf --config path/to/config.yaml # Custom config path
```

```bash
# Or invoke directly without installing:
python main.py                  # equivalent to: edf
python main.py --dry-run        # equivalent to: edf --dry-run
```

---

## Project Status

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | ✅ Complete | Project skeleton, models, logging, CLI bootstrap |
| 2 | ✅ Complete | GSEB adapter, BaseAdapter contract, pre-flight |
| 3 | ✅ Complete | DownloadPipeline, validation, HTTP fetch |
| 4 | ✅ Complete | StorageManager, ManifestManager, checksum registry |
| 5 | ✅ Complete | Hardening, documentation, full verification (174 tests) |
| 6 | ✅ Complete | NCERT adapter, adapter registry, multi-board orchestration (230 tests) |
| 7 | ✅ **Complete** | ConfigLoader, production CLI, integration test suite (309 tests) |

**Phase 5 deliverables**

- `VERIFICATION_REPORT_PHASE5.md` — full verification report.
- `PHASE5_BASELINE.md` — frozen baseline (APIs, modules, risks, Phase 6 prereqs).
- `scripts/verify_all.py` — CI-friendly verification runner.
- Updated `README.md` — architecture, install, tests, status, roadmap.

**Phase 6 deliverables**

- `src/edf/adapters/ncert.py` — NCERT source adapter (pre-flight code verification,
  URL derivation, descriptor generation).
- `src/edf/adapters/registry.py` — `AdapterRegistry` (registration, lookup,
  lazy instantiation, enable/disable board discovery) + `default_registry()` factory.
- `src/edf/core/pipeline.py` — refactored to registry-driven, board-agnostic
  orchestration (no hardcoded adapter imports).
- `src/edf/core/downloader.py` — per-board `RunSummary.board_summaries` aggregation.
- `tests/test_adapter_registry.py` — 48 registry verification tests.
- `tests/test_multiboard_aggregation.py` — 7 per-board summary tests.
- `tests/test_multiboard_integration.py` — 1 full multi-board end-to-end test.
- `.gitignore` — Python bytecode, caches, test artifacts, editor files.

---

## Roadmap
### ✅ Done (Phases 1–6)

- Skeleton, models, structured logging, CLI bootstrap.
- Board-agnostic `BaseAdapter`; GSEB adapter with pre-flight severity model.
- `DownloadPipeline` with HTTP fetch, retry config, validation hooks.
- `StorageManager`: atomic writes, SHA-256 registry, dedup, path sanitization.
- `ManifestManager`: entry registration, metadata, merge.
- Full verification: 174 tests passing, live integration confirmed.
- `NCERTAdapter`: code-based pre-flight, URL derivation, descriptor generation.
- `AdapterRegistry`: registration, lookup, lazy creation, enable/disable board discovery.
- Registry-driven orchestration: board-agnostic pipeline with multi-board summary.
- Full verification: 230 tests passing.

### ⬜ Phase 7 (next)

---

## License

MIT
