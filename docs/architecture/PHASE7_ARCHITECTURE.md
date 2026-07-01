# Phase 7 — Architecture Document

> **Scope:** This document describes the **as-is** architecture of the EDF-L1
> repository at the **Phase 6 release baseline** (commit `ef3ce2f`, v0.6.0),
> identifies the architectural gaps that Phase 7 must close, and proposes the
> target architecture. It is grounded exclusively in the code present in the
> repository at the time of writing. No assumption is made that is not
> supported by a cited module, line, or behavioural test.
>
> **Companion documents:**
> - [`docs/design/PHASE7_TECHNICAL_DESIGN.md`](../design/PHASE7_TECHNICAL_DESIGN.md)
> - [`docs/design/PHASE7_GAP_ANALYSIS.md`](../design/PHASE7_GAP_ANALYSIS.md)

---

## 1. Current Architecture (Phase 6 Baseline)

EDF-L1 is a **board-agnostic** PDF acquisition framework for educational
textbooks. Each source board (currently GSEB and NCERT) is implemented as a
`BaseAdapter` subclass; a shared, registry-driven orchestration core handles
pre-flight, download, validation, content-addressed storage, and manifest
registration.

### 1.1 Module Inventory (as implemented)

| Layer | Module | Class / Functions | Verified? |
|-------|--------|-------------------|-----------|
| Entry point | `main.py` | `main()` | ⚠ Stub — prints `"EDF-L1 Bootstrap Ready"` and exits 0. Does **not** invoke `PipelineOrchestrator`. |
| Config | `src/edf/core/config.py` | `ConfigLoader`, `ConfigValidationError` | ⚠ **Placeholder** — `_load()` returns `{"version": "1.0"}`; `_validate()` is a `pass` stub. |
| Orchestration | `src/edf/core/pipeline.py` | `PipelineOrchestrator` | ✅ Implemented, board-agnostic, registry-driven. |
| Download | `src/edf/core/downloader.py` | `DownloadPipeline` | ✅ Implemented; per-board `RunSummary.board_summaries`. |
| Adapter contract | `src/edf/adapters/base.py` | `BaseAdapter` (ABC) | ✅ Stable contract. |
| GSEB adapter | `src/edf/adapters/gseb.py` | `GSEBAdapter` | ✅ Implemented. |
| NCERT adapter | `src/edf/adapters/ncert.py` | `NCERTAdapter` | ✅ Implemented; template-based URL/filename derivation. |
| Registry | `src/edf/adapters/registry.py` | `AdapterRegistry`, `default_registry()` | ✅ Implemented; lazy adapter instantiation. |
| Storage | `src/edf/storage/manager.py` | `StorageManager` | ✅ Implemented; atomic writes, SHA-256 registry, path sanitization. |
| Manifest | `src/edf/manifests/manager.py` | `ManifestManager` | ✅ Implemented; atomic manifest + checksums persistence. |
| Models | `src/edf/models/data.py` | `DownloadDescriptor`, `ManifestEntry`, `PreflightIssue`, `RunSummary`, `ValidationResult`, enums | ✅ Stable. |
| HTTP utils | `src/edf/utils/http.py` | `download_stream`, `head_request`, `create_session`, `compute_backoff`, `should_retry` | ✅ Implemented (`create_session` docstring is stale; it returns a real `requests.Session`). |
| Hashing utils | `src/edf/utils/hashing.py` | `sha256_file`, `sha256_bytes`, `sha256_stream`, `compare_checksums` | ✅ Implemented. |
| PDF utils | `src/edf/utils/pdf.py` | `validate_pdf_header`, `validate_pdf_size`, `validate_mime_type`, `get_page_count` | ⚠ `get_page_count()` is a `TODO` placeholder returning `None`. |
| Logging | `src/edf/logging/logger.py` | `EDFLogger`, `JSONFormatter` | ✅ Implemented; dual human + JSONL output. |

> **Verification status** reflects the actual code, not README claims. The
> README states "Production ready" and documents a CLI (`--dry-run`,
> `--board`, `--verify-only`); **no such CLI exists in `main.py`**. This is a
> documentation/code mismatch documented in the Gap Analysis.

### 1.2 Architectural Style and Properties

The codebase follows a **layered, dependency-injected** design:

- **Contracts over concretions.** Adapters depend on the `BaseAdapter` ABC.
  The orchestrator depends on the `AdapterRegistry` abstraction, not on
  `GSEBAdapter` or `NCERTAdapter` directly (concrete imports are localized to
  `default_registry()` to avoid circular imports).
- **Pre-flight first.** Adapters classify issues via a `PreflightSeverity`
  enum (`INFO` / `WARNING` / `ERROR`) *before* any download. The orchestrator
  aborts the entire run if any `ERROR` is raised.
- **Content-addressed storage.** Files are placed atomically (temp write →
  `fsync` → `os.replace`) and indexed by SHA-256 in a checksum registry that
  powers dedup.
- **Manifest-tracked.** Every stored file is registered with board / std /
  subject / medium / language / source_url / sha256 / size metadata.
- **Fault isolation per descriptor.** `DownloadPipeline._process_descriptor`
  catches per-file failures; a single descriptor failure does not abort the
  batch (only affects `RunSummary.failed` and the exit code).

### 1.3 Module Interaction Diagram (As-Is)

The diagram below shows the **intended** call graph and annotates the two
broken links (the CLI stub and the placeholder `ConfigLoader`) that prevent
the documented end-to-end path from running.

```
                         ┌──────────────────────────────────┐
                         │  main.py   (⚠ STUB)              │
                         │   main() → prints "Bootstrap"    │
                         │   ✗ never calls orchestrator     │
                         └───────────────┬──────────────────┘
                                         │ (intended, not wired)
                                         ▼
            ┌────────────────────────────────────────────────────┐
            │  config.yaml   (⚠ never read at runtime)           │
            └────────────────────────┬───────────────────────────┘
                                     │  (intended)
                                     ▼
                ┌────────────────────────────────────────────┐
                │  core/config.py  ConfigLoader  (⚠ STUB)    │
                │   _load()     → returns {"version":"1.0"}  │
                │   _validate() → pass                       │
                │   config / general / download / ... props  │
                └────────────────────────┬───────────────────┘
                                         │ dependency injection
                                         ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  core/pipeline.py   PipelineOrchestrator   (✅ implemented)     │
   │   initialize(config_loader, logger) → run() → result dict       │
   │                                                                 │
   │   Phase 0  Inventory        Phase 1  Pre-flight                 │
   │   Phase 2  Collect desc.    Phase 3-5  Download/Validate/Store  │
   │   Phase 6  Manifest save    Phase 7  Summary                    │
   └──────┬──────────────────┬──────────────────────┬───────────────┘
          │                  │                      │
          ▼                  ▼                      ▼
 ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐
 │ adapters/       │  │ core/downloader  │  │ manifests/manager      │
 │  registry.py    │  │  DownloadPipeline│  │  ManifestManager       │
 │  AdapterRegistry│  │  _process_desc() │  │  add_entry/checksum    │
 │  default_reg()  │  │  run() → summary │  │  save() atomic         │
 └────────┬────────┘  └────────┬─────────┘  └────────────────────────┘
          │                    │
          ▼                    ▼
 ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐
 │ adapters/       │  │ storage/manager  │  │ utils/                 │
 │  base.py (ABC)  │  │  StorageManager  │  │  http.py download_stream│
 │  gseb.py        │  │  atomic_place    │  │  hashing.py sha256_*   │
 │  ncert.py       │  │  register_check  │  │  pdf.py validate_*     │
 └─────────────────┘  └──────────────────┘  └────────────────────────┘
                                                   │
                                                   ▼
                                          ┌────────────────────────┐
                                          │ logging/logger.py      │
                                          │  EDFLogger (log+jsonl) │
                                          └────────────────────────┘
```

**Legend:** ✅ = implemented and exercised by tests; ⚠ = placeholder/stub;
✗ = intended but not wired.

### 1.4 Component Lifecycle

The intended lifecycle (per `PipelineOrchestrator` docstrings) is:

1. `ConfigLoader(config_path)` loads + validates `config.yaml`.
2. `EDFLogger(run_id, log_dir)` is constructed.
3. `PipelineOrchestrator().initialize(config_loader, logger)`.
4. `orchestrator.run()` internally:
   - constructs `StorageManager`, `ManifestManager`;
   - obtains `default_registry()` and resolves enabled boards;
   - instantiates adapters lazily via `registry.create(board, config)`;
   - runs pre-flight → collect → download → manifest → summary.
5. `orchestrator.shutdown()`.

> **Current reality:** Steps 1–2 are never performed by `main.py`, and
> Step 1's loader is a stub. The lifecycle is only proven in tests that
> hand-craft a `config` dict and a `SimpleNamespace` config-loader stand-in
> (see `tests/test_multiboard_integration.py:90-97`).

---

## 2. Architectural Gaps Driving Phase 7

The following gaps are architectural (structural), not merely feature
requests. They are ranked here at a summary level; per-gap detail and
justification live in the Gap Analysis.

| # | Gap | Severity | Layer affected |
|---|-----|----------|----------------|
| G1 | `ConfigLoader` is a placeholder; `config.yaml` is never read or validated | **Critical** | Config |
| G2 | `main.py` is a bootstrap stub; no CLI, no orchestrator invocation | **Critical** | Entry point |
| G3 | Documented CLI flags (`--dry-run`, `--board`, `--verify-only`) do not exist | **Critical** | Entry point / docs |
| G4 | End-to-end path (`config.yaml` → storage on disk) is untested | **High** | Testing |
| G5 | `http_client` parameter is plumbed through adapters but never used | **Medium** | Adapters |
| G6 | `get_page_count()` is a `TODO` returning `None` | **Low** | Validation |
| G7 | README claims "Production ready" with a CLI that does not exist | **High** | Documentation |
| G8 | No graceful handling of the dry-run flag inside the pipeline | **High** | Orchestration |

> G1, G2, G3 are the reasons **ConfigLoader and CLI are the highest-priority
> Phase 7 deliverables** — see §4.

---

## 3. Target Architecture (Phase 7)

Phase 7 must **complete the wiring** without redesigning the stable core
(adapters, registry, storage, manifest, models). The target preserves the
existing contracts and adds the two missing entry edges of the call graph.

### 3.1 Design Principles for Phase 7

1. **No breaking changes to existing public APIs.** `BaseAdapter`,
   `AdapterRegistry`, `StorageManager`, `ManifestManager`, and the data
   models are frozen. Phase 7 *consumes* them, not *modifies* them.
2. **Fail fast on misconfiguration.** `ConfigLoader` must raise
   `ConfigValidationError` with a precise message before the pipeline starts,
   so a bad `config.yaml` never produces a partial/corrupt CONTENT tree.
3. **CLI is a thin composition root.** Argument parsing must not embed
   business logic; it constructs `ConfigLoader` + `EDFLogger` +
   `PipelineOrchestrator` and delegates.
4. **Defaults must be explicit and documented.** Every config key consumed by
   the core already has an inline default (see §3.3). Phase 7 makes those
   defaults the *single source of truth* and removes ad-hoc `.get(..., x)`
   fallbacks where feasible.

### 3.2 Target Module Interaction Diagram

```
   $ edf run --config config.yaml            (or)   $ python -m edf ...
            │
            ▼
   ┌─────────────────────────────────────────────────────────┐
   │  NEW: cli entry (e.g. src/edf/cli.py or main.py rewrite)│
   │   argparse: --config, --dry-run, --board, --verify-only │
   │   build objects → invoke orchestrator → map exit code   │
   └────────┬───────────────────────────────────┬────────────┘
            │                                   │
            ▼                                   ▼
 ┌────────────────────────┐         ┌──────────────────────────┐
 │ ConfigLoader (REWORKED)│         │ EDFLogger(run_id, log_dir)│
 │  _load()   → read YAML │         │  (unchanged)             │
 │  _validate()→ checks   │         └──────────────────────────┘
 │  typed accessors       │
 └───────────┬────────────┘
             │  config_loader.config  (validated dict)
             ▼
   ┌─────────────────────────────────────────────────────────┐
   │  PipelineOrchestrator   (unchanged public surface)       │
   │   initialize(config_loader, logger)                      │
   │   run() → honors config_loader.is_dry_run                │
   └─────────────────────────────────────────────────────────┘
             │
             ▼   (existing, stable core — unchanged)
        adapters/registry → adapters/{gseb,ncert}
        core/downloader → storage + manifests + utils
```

### 3.3 Configuration Surface Already Consumed by the Core

The following config keys are **already read** by existing code (via
`config.get(...)`). Phase 7 validation must enforce these as the contract;
this list is extracted directly from the source.

| Key path | Consumer (file:line) | Default in code |
|----------|----------------------|-----------------|
| `general.content_root` | `config.py:100`, `pipeline.py:108` | `"./CONTENT"` |
| `general.edf_metadata_dir` | `config.py:105`, `pipeline.py:109` | `".edf"` |
| `general.dry_run` | `config.py:110` | `False` |
| `general.force_overwrite` | `config.py:115`, `pipeline.py:227` | `False` |
| `download.max_retries` | `downloader.py:207` | `3` |
| `download.timeout_seconds` | `downloader.py:208` | `120` |
| `download.chunk_size_bytes` * | `downloader.py:209` | `8192` |
| `validation.min_size_bytes` | `downloader.py:387` | `10240` |
| `validation.max_size_bytes` | `downloader.py:388` | `None` |
| `gseb.textbooks[]` | `gseb.py:65` | `[]` |
| `ncert.textbooks[]` | `ncert.py:106` | `[]` |
| `ncert.url_template` | `ncert.py:109` | `DEFAULT_URL_TEMPLATE` |
| `ncert.filename_template` | `ncert.py:112` | `DEFAULT_FILENAME_TEMPLATE` |
| `ncert.master_list_url` | `ncert.py:115` | `None` (informational only) |
| `boards.<board>.enabled` | `registry.py:226` | absent ⇒ enabled |

\* Note: `downloader.py:209` reads `chunk_size` (not `chunk_size_bytes`);
`config.yaml.example` documents `chunk_size_bytes`. This is a **latent key
mismatch** — see Gap Analysis G9.

### 3.4 Why the Core Does Not Need Refactoring

The orchestrator and pipeline already accept a `config` dict and derive all
runtime behaviour from it. The *only* structural defects are the two entry
edges (loader + CLI) and the dry-run propagation. Everything downstream of a
validated `config` dict is sound and test-covered. This is why Phase 7 is
scoped as **completion**, not redesign.

---

## 4. Why ConfigLoader and CLI Are the Highest-Priority Deliverables

These two artefacts are the **single points of failure** that currently make
the entire framework unusable from the documented entry point.

1. **They are the only unimplemented links in the call graph.** Every other
   component (adapters, registry, downloader, storage, manifest, utils,
   logging) is implemented and unit-tested. The chain breaks at exactly two
   places: reading `config.yaml`, and being invoked from the command line.
2. **Their absence is silently masked.** `ConfigLoader.__init__` does not
   raise on a missing file — it returns a hardcoded `{"version": "1.0"}`.
   A user following the README (`cp config.yaml.example config.yaml; python
   main.py`) will see "Bootstrap Ready" and believe the pipeline ran, while
   in reality nothing was loaded, validated, or downloaded. This is the most
   dangerous failure mode: **silent no-op masquerading as success**.
3. **Every other Phase 7 capability depends on them.** Dry-run enforcement
   (G8), end-to-end testing (G4), and CI wiring all require a real config
   object flowing from a real loader through a real entry point. Nothing else
   can be meaningfully verified until these exist.
4. **They are low-risk to implement.** Because the core already consumes a
   plain `dict`, ConfigLoader only needs to *produce* that dict from YAML and
   *validate* it. The CLI only needs to *compose* existing objects. Neither
   touches the frozen core.

---

## 5. Architectural Risks (Summary)

Detailed in the Gap Analysis; summarized here for the architecture view.

- **R1 — Silent no-op risk:** the placeholder loader returns valid-looking
  data, so misconfiguration does not fail loudly. Mitigation: `_validate()`
  must reject empty/missing `content_root`, missing `textbooks`, and unknown
  schema versions.
- **R2 — Untested end-to-end path:** no test loads a real YAML file through
  `ConfigLoader` into `PipelineOrchestrator`. Mitigation: a Phase 7
  integration test that reads a temp `config.yaml`.
- **R3 — Documentation drift:** README documents CLI flags and "Production
  ready" status that the code does not support. Mitigation: align docs only
  after the CLI lands (out of Milestone 1 scope per the constraints, but
  flagged).
- **R4 — Key-name drift:** `chunk_size_bytes` (config example, docstrings)
  vs `chunk_size` (downloader code). Mitigation: validation must canonicalize
  or reject.

---

## 6. References

- Phase 6 baseline: commit `ef3ce2f` ("Merge branch 'phase6-ncert'").
- Source of truth modules: `src/edf/core/config.py`, `src/edf/core/pipeline.py`,
  `src/edf/core/downloader.py`, `src/edf/adapters/*.py`,
  `src/edf/storage/manager.py`, `src/edf/manifests/manager.py`,
  `src/edf/models/data.py`, `src/edf/utils/*.py`, `src/edf/logging/logger.py`.
- Test evidence: `tests/test_multiboard_integration.py` (uses a
  `SimpleNamespace` config stand-in, confirming the real loader is bypassed).
- Configuration template: `config/config.yaml.example`.
