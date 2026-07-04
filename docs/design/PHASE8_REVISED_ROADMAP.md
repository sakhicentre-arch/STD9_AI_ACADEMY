# Phase 8 Revised Roadmap — EDF-L1 v0.8.0

> **Status:** Draft for Approval
> **Date:** 2026-07-04
> **Baseline:** v0.7.0
> **Target:** v0.8.0

---

## 1. Overview

This roadmap organizes the revised Phase 8 into four milestones, totaling approximately 4 development weeks. Each milestone is self-contained with clear objectives, deliverables, and release criteria.

### Milestone Summary

```
  Phase 8A          Phase 8B          Phase 8C          Phase 8D
  Reliability       Performance       Packaging         Dev Experience
  ──────────       ──────────        ──────────        ──────────
  Checkpoint/       Parallel DLs,     PyPI package,     Manifest diff,
  Resume, Graceful  Progress,         Dockerfile,       JSON output,
  Shutdown          Rate Limits       CI improvements   CLI subcommands
       │                 │                │                 │
       ▼                 ▼                ▼                 ▼
     Week 1            Week 2           Week 3            Week 4
```

**Dependency graph:**

```
8A ──→ 8B ──→ 8C ──→ 8D
```

Milestones execute strictly in sequence: **8A → 8B → 8C → 8D**. No overlap is planned between milestones. Each milestone depends on all prior milestones being complete:

- **8B** depends on **8A** (checkpoint integration must work correctly with parallel writes).
- **8C** depends on **8B** (all new source code is finalized before packaging).
- **8D** depends on **8A** (checkpoint for resume subcommand context), **8B** (progress data for JSON output), and **8C** (packaging — docs should reference install methods).

The sequential ordering ensures each milestone builds on a stable, fully-tested predecessor.

---

## 2. Phase 8A — Reliability

### 2.1 Objectives

- Make downloads resumable after interruption
- Handle Ctrl+C gracefully without corrupting state
- Persist progress so users never lose work

### 2.2 Deliverables

| ID | Deliverable | Description |
|----|------------|-------------|
| 8A-D1 | Checkpoint Manager | `src/edf/core/checkpoint.py` — persist completed/failed descriptor status to `.edf/checkpoint.json` |
| 8A-D2 | Resume Logic | `--resume` flag in CLI; `DownloadPipeline` loads checkpoint and skips completed entries |
| 8A-D3 | Graceful Shutdown | SIGINT/SIGTERM handler in `PipelineOrchestrator.run()` that completes current descriptor, saves checkpoint, and exits |
| 8A-D4 | Config Validation Extensions | V11-V14 validation rules for new config keys |
| 8A-D5 | Checkpoint Expiry | Auto-expire checkpoints older than `checkpoint.max_age_hours` (default 7 days) |

### 2.3 Files Likely to Change

| File | Change Type | Description |
|------|------------|-------------|
| `src/edf/core/checkpoint.py` | **New** | Checkpoint manager module |
| `src/edf/core/downloader.py` | Modify | Write checkpoint after each successful download; load checkpoint on init |
| `src/edf/core/pipeline.py` | Modify | SIGINT handler, checkpoint integration, pass checkpoint to DownloadPipeline |
| `src/edf/core/config.py` | Modify | Add V11-V14 validation rules, new defaults |
| `main.py` | Modify | Add `--resume` flag |
| `config/config.yaml.example` | Modify | Document `checkpoint` section |

### 2.4 Estimated Effort

| Task | Effort |
|------|--------|
| Checkpoint Manager (design + implement + test) | 2 days |
| Resume Logic (implement + test) | 1 day |
| Graceful Shutdown (implement + test) | 1 day |
| Config Validation Extensions | 0.5 days |
| Integration testing | 0.5 days |
| **Total** | **5 days (1 week)** |

### 2.5 Dependencies

- None (first milestone, builds on v0.7.0 baseline)

### 2.6 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Checkpoint file corruption on hard crash | Low | Medium | Atomic writes via `StorageManager`; checksum on load |
| SIGINT handler conflicts with pytest | Medium | Low | Gate handler behind `--resume` or check for test environment |
| Windows signal handling differences | Medium | Low | Test on Windows; `signal.SIGINT` works on both platforms |
| Descriptor key collision between runs | Low | Medium | Include run_id in checkpoint or use content-addressed keys |

### 2.7 Test Strategy

- **Unit tests:** Checkpoint write/read/clear/expiry (~15 tests)
- **Unit tests:** Resume logic — skip completed, re-attempt failed (~8 tests)
- **Integration tests:** SIGINT during multi-file download, verify checkpoint saved (~5 tests)
- **Unit tests:** Config validation V11-V14 (~8 tests)

**Estimated new tests:** ~36

### 2.8 Release Criteria

- [ ] `--resume` skips previously completed downloads
- [ ] Ctrl+C during download saves checkpoint to `.edf/checkpoint.json`
- [ ] Orphaned temp files are cleaned up on interrupt
- [ ] Checkpoint expiry removes stale entries
- [ ] All existing tests pass unchanged
- [ ] New test coverage ≥ 90% for checkpoint module

---

## 3. Phase 8B — Performance

### 3.1 Objectives

- Add optional parallel downloads for faster bulk operations
- Display download progress with per-file speed estimates
- Add per-board rate limiting

### 3.2 Deliverables

| ID | Deliverable | Description |
|----|------------|-------------|
| 8B-D1 | Progress Tracker | `src/edf/core/progress.py` — per-file progress tracking with bytes/sec computation |
| 8B-D2 | Progress Display | Integrate with `download_stream()` via callback; emit progress to logger |
| 8B-D3 | Parallel Downloads | Optional `--parallel N` flag; `ThreadPoolExecutor` in `DownloadPipeline` with bounded concurrency |
| 8B-D4 | Per-Board Rate Limits | `per_board_delay` and `rate_limit_rpm` config keys; enforce in DownloadPipeline |
| 8B-D5 | `--progress` Flag | CLI flag to enable/disable progress display (default: enabled) |

### 3.3 Files Likely to Change

| File | Change Type | Description |
|------|------------|-------------|
| `src/edf/core/progress.py` | **New** | Progress tracking module |
| `src/edf/core/downloader.py` | Modify | Accept progress callback; thread-safe checkpoint writes; parallel dispatch |
| `src/edf/utils/http.py` | Modify | Progress callback parameter in `download_stream()` |
| `src/edf/core/config.py` | Modify | New defaults for `parallel_max`, `per_board_delay` |
| `main.py` | Modify | Add `--parallel N` and `--progress` flags |
| `config/config.yaml.example` | Modify | Document `download.parallel_max`, `per_board_delay`, board rate limits |

### 3.4 Estimated Effort

| Task | Effort |
|------|--------|
| Progress Tracker (design + implement + test) | 1.5 days |
| Progress Display in download_stream | 0.5 days |
| Parallel Downloads (implement + test) | 1.5 days |
| Per-Board Rate Limits (implement + test) | 1 day |
| Integration testing | 0.5 days |
| **Total** | **5 days (1 week)** |

### 3.5 Dependencies

- **8A:** Checkpoint integration must work correctly with parallel writes (serialized checkpoint writes)
- No external dependencies

### 3.6 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Thread safety in checkpoint writes | Medium | High | Use a threading.Lock for checkpoint file access |
| Server-side rate limiting rejects parallel requests | Medium | Medium | Per-board rate_limit_rpm config; default conservative (sequential) |
| Progress display garbled in parallel mode | Medium | Low | Use logger (serialized output), not direct stdout |
| ThreadPoolExecutor overhead for small N | Low | Low | Only enable when `parallel_max > 1`; benchmark minimum useful N |

### 3.7 Test Strategy

- **Unit tests:** Progress computation — bytes/sec, elapsed time, unknown total (~10 tests)
- **Unit tests:** Parallel dispatch — N descriptors, M workers, correct ordering (~10 tests)
- **Unit tests:** Rate limiting — per-board delay, rpm enforcement (~6 tests)
- **Integration tests:** Parallel + checkpoint combined; progress + resume combined (~5 tests)

**Estimated new tests:** ~31

### 3.8 Release Criteria

- [ ] `--parallel 2` completes a 10-file download faster than sequential
- [ ] Progress display shows filename, percentage, speed for each file
- [ ] Checkpoint writes are thread-safe under parallel execution
- [ ] Per-board rate limiting respects configured RPM
- [ ] `--parallel 1` produces identical behavior to v0.7.0 (no regression)
- [ ] All existing tests pass unchanged

---

## 4. Phase 8C — Packaging & Distribution

### 4.1 Objectives

- Make EDF-L1 installable via `pip install edf-l1` from PyPI
- Provide a Dockerfile for containerized usage
- Improve CI pipeline

### 4.2 Deliverables

| ID | Deliverable | Description |
|----|------------|-------------|
| 8C-D1 | PyPI Packaging | Finalize `pyproject.toml` build metadata; ensure `pip install .` works; prepare for PyPI upload |
| 8C-D2 | Dockerfile | Multi-stage Dockerfile (builder → slim runtime) |
| 8C-D3 | CI Improvements | Add coverage gate (≥85%), add lint step (ruff/flake8), matrix test on Python 3.10/3.11/3.12 |
| 8C-D4 | `.gitignore` Updates | Exclude build artifacts, dist/, *.egg-info |

### 4.3 Files Likely to Change

| File | Change Type | Description |
|------|------------|-------------|
| `pyproject.toml` | Modify | Finalize build metadata, classifiers, entry points |
| `Dockerfile` | **New** | Multi-stage container image |
| `.dockerignore` | **New** | Exclude unnecessary files from Docker context |
| `.github/workflows/test.yml` | **New** or Modify | CI pipeline with coverage gate and lint |
| `.gitignore` | Modify | Add build artifact patterns |

### 4.4 Estimated Effort

| Task | Effort |
|------|--------|
| PyPI Packaging (metadata, test install, wheel build) | 1.5 days |
| Dockerfile (build, test, optimize size) | 1 day |
| CI Improvements (workflow, matrix, coverage gate) | 1.5 days |
| Documentation updates | 0.5 days |
| **Total** | **~4.5 days (1 week with buffer)** |

### 4.5 Dependencies

- 8B complete (all new source code finalized before packaging)

### 4.6 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `pyproject.toml` changes break existing install flow | Low | High | Test `pip install .` and `pip install -r requirements.txt` both work |
| Docker image too large | Low | Low | Multi-stage build; base on python:3.10-slim |
| PyPI name conflict | Low | Medium | Check `edf-l1` availability early; fallback to `edf-l1-dl` |
| CI matrix reveals platform-specific failures | Medium | Medium | Fix issues as found; gate on pass rate |

### 4.7 Test Strategy

- **Build tests:** `python -m build` produces valid wheel + sdist
- **Install tests:** `pip install .` in clean venv; `edf --help` works
- **Docker tests:** Build image, run `edf validate-config` inside container
- **CI tests:** Workflow runs on all matrix entries

**Estimated new tests:** 0 (infrastructure, not code tests — but CI validates existing tests)

### 4.8 Release Criteria

- [ ] `pip install .` succeeds in clean venv
- [ ] `edf --help` displays all flags including new Phase 8 flags
- [ ] Docker image builds and runs `edf validate-config` successfully
- [ ] Docker image ≤ 200 MB
- [ ] CI workflow passes on Python 3.10, 3.11, 3.12
- [ ] Coverage gate enforces ≥ 85%

---

## 5. Phase 8D — Developer Experience

### 5.1 Objectives

- Provide manifest diffing capability
- Add JSON output mode for programmatic consumption
- Improve CLI with subcommands for common tasks
- Better documentation

### 5.2 Deliverables

| ID | Deliverable | Description |
|----|------------|-------------|
| 8D-D1 | Manifest Diff | `src/edf/manifests/diff.py` — compare two manifest snapshots |
| 8D-D2 | `edf diff` Subcommand | CLI subcommand to compare manifest files |
| 8D-D3 | JSON Output Mode | `--json` flag; `PipelineOrchestrator.run()` result as JSON to stdout |
| 8D-D4 | `edf validate-config` Subcommand | Validate config and print result, exit 0 or 2 |
| 8D-D5 | Documentation Updates | Update README with new CLI flags, examples, and usage patterns |

### 5.3 Files Likely to Change

| File | Change Type | Description |
|------|------------|-------------|
| `src/edf/manifests/diff.py` | **New** | Manifest comparison logic |
| `main.py` | Modify | Add subcommand parser; add `--json`; wire diff and validate-config |
| `src/edf/core/pipeline.py` | Modify | JSON serialization of result dict |
| `src/edf/core/config.py` | Modify | Expose validation method for standalone use |

### 5.4 Estimated Effort

| Task | Effort |
|------|--------|
| Manifest Diff (design + implement + test) | 1.5 days |
| CLI Subcommands (implement + test) | 1.5 days |
| JSON Output Mode (implement + test) | 1 day |
| Documentation Updates | 0.5 days |
| Integration testing | 0.5 days |
| **Total** | **5 days (1 week)** |

### 5.5 Dependencies

- 8A (checkpoint for resume subcommand context)
- 8B (progress data for JSON output)
- 8C (packaging — docs should reference install methods)

### 5.6 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Subcommand parser breaks existing `edf run` invocation | Low | High | Thorough backward-compat testing; `run` as default subcommand |
| JSON output contains sensitive data | Low | Low | Review output fields; exclude API keys/URLs if present |
| Manifest diff on large manifests is slow | Low | Low | Manifests are small (< 1000 entries typical); no optimization needed |

### 5.7 Test Strategy

- **Unit tests:** Manifest diff — added/removed/changed/unchanged (~12 tests)
- **Unit tests:** JSON output — valid JSON, correct schema, all fields present (~6 tests)
- **CLI tests:** Subcommand routing, validate-config exit codes (~6 tests)
- **Integration tests:** Full diff workflow with real manifest files (~3 tests)

**Estimated new tests:** ~27

### 5.8 Release Criteria

- [ ] `edf diff --before manifest_old.json --after manifest_new.json` shows correct diff
- [ ] `--json` produces valid JSON with all expected fields
- [ ] `edf validate-config config.yaml` exits 0 for valid, 2 for invalid
- [ ] `edf run --config config.yaml` still works as before (backward compat)
- [ ] Documentation covers all new features
- [ ] All existing tests pass unchanged

---

## 6. Timeline Summary

| Week | Milestone | Focus | New Tests (est.) | Cumulative Tests |
|------|-----------|-------|------------------|------------------|
| 1 | 8A Reliability | Checkpoint, Resume, Graceful Shutdown | ~36 | ~345 |
| 2 | 8B Performance | Parallel DLs, Progress, Rate Limits | ~31 | ~376 |
| 3 | 8C Packaging | PyPI, Dockerfile, CI | 0 | ~376 |
| 4 | 8D Developer Experience | Manifest Diff, JSON, Subcommands | ~27 | ~403 |

**Total:** 4 weeks, ~94 new tests, ~403 total tests

---

## 7. Release Strategy

### Versioning

- Phase 8 targets release **v0.8.0** (minor version bump — additive features, no breaking changes)

### Branch Strategy

```
master (v0.7.0)
  │
  └── phase8
       ├── phase8/8a-reliability
       ├── phase8/8b-performance
       ├── phase8/8c-packaging
       └── phase8/8d-dev-experience
```

Each milestone branch is merged into `phase8` via PR. Final `phase8` branch is merged into `master` for v0.8.0 release.

### Release Artifacts

- Source tag on GitHub
- Wheel + sdist on PyPI
- Docker image (optional, separate build)
- CHANGELOG.md entry

---

## 8. Comparison with Rejected Roadmap

| Dimension | Rejected Roadmap | Revised Roadmap |
|-----------|-----------------|----------------|
| Milestones | 6 (Observability, Security, Performance, Extensibility, Deployment, Operational Excellence) | 4 (Reliability, Performance, Packaging, Dev Experience) |
| Duration | 21 weeks | 4 weeks |
| Items | 41 | ~20 |
| Story points | 165 | ~50 |
| New dependencies | 6+ (Prometheus, OpenTelemetry, Vault, K8s, etc.) | 0 |
| Architecture changes | Major (async, REST API, plugin lifecycle, container-native) | Minor (3 new modules, CLI extensions) |
| Paradigm shift | Yes (CLI → service) | No |
| Risk profile | High (many unproven technologies) | Low (evolutionary, proven patterns) |

---

*End of PHASE8_REVISED_ROADMAP.md*
