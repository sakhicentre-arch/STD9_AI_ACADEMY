# Phase 8 Revised Architecture — EDF-L1 Reliability and Operability

**Document Status:** Draft for Approval (replaces rejected PHASE8_ARCHITECTURE.md)
**Baseline Release:** v0.7.0 (Phase 7D — Release Engineering)
**Target Release:** v0.8.0 (Phase 8 — Reliability & Operability)
**Author:** Architecture Review (revised per independent review)
**Last Updated:** 2026-07-03

---

## 1. Executive Summary

EDF-L1 v0.7.0 is a production-ready batch PDF download framework for educational textbooks (GSEB, NCERT). It processes textbook configuration from `config.yaml`, downloads PDFs sequentially via board-specific adapters, validates them, and registers them in a content-addressed manifest. The system runs as a CLI tool (`edf`), completes its work, and exits.

Phase 8 focuses on **reliability and operability** improvements that directly benefit the textbook download workflow: graceful interrupt handling, download resumption, optional parallel downloads, better CLI output, packaging for standard Python distribution, and CI quality gates.

This plan preserves every existing module and interface. No architectural redesign. No new subsystems. No paradigm shift.

---

## 2. Architecture Review (Current State — v0.7.0)

### 2.1 Actual Component Inventory

Every component listed below exists in the repository at v0.7.0 and is exercised by the 309-test suite.

| Module | Class/Functions | File | Responsibility |
|--------|----------------|------|-----------------|
| Entry point | `main()`, `build_parser()`, `build_orchestrator()` | `main.py` | CLI argument parsing, composition root |
| Config | `ConfigLoader`, `ConfigValidationError` | `src/edf/core/config.py` | YAML loading, validation, typed accessors |
| Orchestration | `PipelineOrchestrator` | `src/edf/core/pipeline.py` | End-to-end pipeline sequencing |
| Download | `DownloadPipeline` | `src/edf/core/downloader.py` | Per-file download → validate → place → register |
| Adapter contract | `BaseAdapter` (ABC) | `src/edf/adapters/base.py` | Abstract interface for board adapters |
| GSEB adapter | `GSEBAdapter` | `src/edf/adapters/gseb.py` | GSEB textbook descriptor generation |
| NCERT adapter | `NCERTAdapter` | `src/edf/adapters/ncert.py` | NCERT textbook descriptor generation |
| Registry | `AdapterRegistry`, `default_registry()` | `src/edf/adapters/registry.py` | Board discovery, enable/disable, lazy instantiation |
| Storage | `StorageManager` | `src/edf/storage/manager.py` | Atomic writes, SHA-256 registry, dedup, path sanitization |
| Manifest | `ManifestManager` | `src/edf/manifests/manager.py` | Entry registration, merging, persistence |
| Models | `DownloadDescriptor`, `ManifestEntry`, `PreflightIssue`, `RunSummary`, `ValidationResult`, enums | `src/edf/models/data.py` | Canonical data types |
| HTTP utils | `download_stream()`, `head_request()`, `create_session()` | `src/edf/utils/http.py` | HTTP fetching with retry |
| Hashing | `sha256_file()`, `sha256_bytes()`, `compare_checksums()` | `src/edf/utils/hashing.py` | Checksum computation |
| PDF utils | `validate_pdf_header()`, `validate_pdf_size()` | `src/edf/utils/pdf.py` | PDF validation gates |
| Logging | `EDFLogger`, `JSONFormatter` | `src/edf/logging/logger.py` | Structured dual-output logging (human + JSONL) |

### 2.2 Actual Call Graph

```
  edf [--config PATH] [--dry-run] [--board NAME] [--verify-only]
    │
    ▼
  main.py :: build_parser() → parse_args()
    │
    ▼
  ConfigLoader(config_path)
    │  validates YAML, applies defaults, returns dict
    ▼
  EDFLogger(run_id, log_dir, level)
    │
    ▼
  PipelineOrchestrator.initialize(config_loader, logger)
    │
    ▼
  PipelineOrchestrator.run(board?, verify_only?)
    │
    ├── Phase 0: Inventory (manifest.discover_existing_files)
    ├── Phase 1: Pre-flight (adapter.pre_flight())
    ├── Phase 2: Collect (adapter.get_descriptors())
    ├── Phase 3-5: Download/Validate/Store
    │     │
    │     ▼
    │   DownloadPipeline.run(descriptors)
    │     └── for each descriptor:
    │           ├── StorageManager.file_exists() (dedup check)
    │           ├── download_stream() (HTTP fetch to temp)
    │           ├── validate_pdf_header/size/checksum
    │           ├── StorageManager.atomic_place()
    │           └── ManifestManager.add_entry()
    │
    ├── Phase 6: Manifest save
    └── Phase 7: Summary
```

### 2.3 Key Design Properties (Established, Preserved)

1. **Adapter-driven extensibility.** New boards implement `BaseAdapter` and register via `AdapterRegistry`. No core changes required.
2. **Content-addressed storage.** SHA-256 registry powers dedup. Atomic writes prevent corruption.
3. **Manifest-tracked.** Every file registered with full metadata. Manifest is the source of truth.
4. **Fault isolation per descriptor.** Single file failure does not abort the batch.
5. **Configuration-driven.** All runtime behaviour derived from `config.yaml` with sensible defaults.
6. **Structured logging.** Dual human + JSONL output with run_id correlation.

---

## 3. Target Architecture (v0.8.0)

### 3.1 What Changes

Phase 8 is **strictly additive**. No existing interface is modified. No module is removed or rewritten.

```
  main.py :: build_parser()          ← EXTENDED: new CLI flags + subcommands
    │
    ▼
  ConfigLoader(config_path)           ← EXTENDED: per-board rate limits
    │
    ▼
  EDFLogger(run_id, log_dir, level)  ← EXTENDED: download progress, timing
    │
    ▼
  PipelineOrchestrator.run()         ← EXTENDED: graceful shutdown, JSON output
    │
    ├── CheckpointManager (NEW)      ← NEW: run state persistence for resume
    │
    ├── DownloadPipeline.run()       ← EXTENDED: optional parallel, bounded concurrency
    │     └── per descriptor:
    │           ├── (existing dedup → download → validate → place → register)
    │           ├── ProgressTracker (NEW) ← per-file progress logging
    │           └── CheckpointManager.mark_completed()
    │
    └── ManifestDiff (NEW)   ← NEW: compare manifests across runs
```

### 3.2 New Modules

| Module | Responsibility | Lines (est.) |
|--------|----------------|--------------|
| `src/edf/core/checkpoint.py` | Persist run state (completed/failed/pending descriptors) to enable resume | ~80 |
| `src/edf/core/progress.py` | Per-file download progress tracking and logging | ~40 |
| `src/edf/manifests/diff.py` | Compare two manifest snapshots, report additions/removals/changes | ~60 |

**Total new code: ~180 lines** across 3 small modules.

### 3.3 What Does NOT Change

| Preserved Interface | Why |
|---|---|
| `BaseAdapter` ABC | Board adapter contract is stable. |
| `AdapterRegistry` | Discovery mechanism is stable. |
| `ConfigLoader` public API | Extended (new config keys), not modified. |
| `PipelineOrchestrator` public API | `initialize()` and `run()` signatures unchanged. |
| `DownloadPipeline` public API | `run()` signature unchanged. New behavior is config-gated. |
| `StorageManager` | Unchanged. |
| `ManifestManager` | Unchanged. |
| All data models | `DownloadDescriptor`, `ManifestEntry`, `RunSummary` etc. unchanged. |
| `EDFLogger` public API | Existing methods unchanged. New capabilities are additive. |

### 3.4 Architectural Principles

All Phase 7 principles carry forward. Phase 8 adds:

7. **Interruptible by default.** A Ctrl+C during a long run should not corrupt state; it should save progress and allow resumption.
8. **Observable without infrastructure.** Progress and results are logged to files, not pushed to external systems.
9. **Packaged as a standard Python tool.** Installable via `pip install edf-l1`, runnable as `edf`.

---

## 4. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Backward Compatibility | No breaking changes to any existing public API. Existing adapters, configs, and tests work unmodified. |
| Performance | No regression on sequential (default) path. Parallel path is opt-in. |
| Dependencies | Minimal new dependencies. Target: 0 new runtime dependencies. |
| Test Coverage | Maintain ≥ 80% on `src/edf/` (current gate). New modules at ≥ 90%. |
| Release | v0.8.0 minor bump. PyPI-publishable. |
| Documentation | Updated README sections, operator notes, upgrade guide. |

---

## 5. References

- `docs/architecture/PHASE7_ARCHITECTURE.md` — Phase 7 baseline (the authoritative architecture)
- `docs/design/PHASE8_GAP_ANALYSIS.md` — gap analysis (input to revised plan)
- `docs/design/PHASE8_REVISED_ROADMAP.md` — revised roadmap
- `docs/design/PHASE8_REVISED_IMPLEMENTATION_PLAN.md` — revised implementation plan
- `docs/design/PHASE8_REVISED_BACKLOG.md` — revised backlog
- `docs/design/PHASE8_REVISED_RISK_REGISTER.md` — revised risk register
