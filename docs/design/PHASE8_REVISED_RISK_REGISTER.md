# Phase 8 Revised Risk Register — EDF-L1 v0.8.0

> **Status:** Draft for Approval
> **Date:** 2026-07-04
> **Baseline:** v0.7.0
> **Target:** v0.8.0

---

## Risk Assessment Matrix

| Likelihood | Impact |
|-----------|--------|
| **Low** | Unlikely to occur or easily prevented |
| **Medium** | Possible; has occurred in similar projects |
| **High** | Likely or has precedent in this codebase |

Risk score = Likelihood × Impact. Items with score ≥ 6 are tracked as "elevated."

---

## Risk Register

### R-01: Checkpoint file corruption on hard crash

| Field | Value |
|-------|-------|
| **ID** | R-01 |
| **Category** | Reliability |
| **Description** | If the process is killed (SIGKILL) or the machine crashes during a checkpoint write, `checkpoint.json` could be left in a corrupt state. Loading a corrupt checkpoint could skip files that weren't actually downloaded, or re-download files that were. |
| **Likelihood** | Low |
| **Impact** | Medium |
| **Score** | 3 |
| **Affected Milestone** | 8A |
| **Mitigation** | Use `StorageManager.atomic_write_bytes()` (temp file + fsync + os.replace) for all checkpoint writes. Validate JSON on load; if corrupt, log warning and start fresh (empty checkpoint). Checksum validation of downloaded files provides a second safety net — even if checkpoint skips a file, the duplicate detection in DownloadPipeline will catch it. |
| **Residual Risk** | Low — Atomic writes and JSON validation make corruption extremely unlikely. |
| **Owner** | 8A implementation |

### R-02: SIGINT handler conflicts with pytest

| Field | Value |
|-------|-------|
| **ID** | R-02 |
| **Category** | Testing |
| **Description** | pytest installs its own SIGINT handler. If `PipelineOrchestrator.run()` installs a custom handler, it could interfere with pytest's test interruption behavior. |
| **Likelihood** | Medium |
| **Impact** | Low |
| **Score** | 3 |
| **Affected Milestone** | 8A |
| **Mitigation** | Only install the handler when NOT running under pytest (check `sys.modules.get("pytest")` or use an environment variable). Alternatively, make handler installation configurable via a parameter in `run()`. Unit tests can test `_handle_shutdown()` directly without signal registration. |
| **Residual Risk** | Low — Testable in isolation. |
| **Owner** | 8A implementation |

### R-03: Windows signal handling differences

| Field | Value |
|-------|-------|
| **ID** | R-03 |
| **Category** | Platform Compatibility |
| **Description** | The primary development platform is Windows (per project environment). `signal.SIGINT` works on Windows but `signal.SIGTERM` does not. If both are registered, SIGTERM registration will fail on Windows. |
| **Likelihood** | Medium |
| **Impact** | Low |
| **Score** | 3 |
| **Affected Milestone** | 8A |
| **Mitigation** | Only register `signal.SIGINT` (works on both Windows and Linux/macOS). Do not register SIGTERM. Alternatively, use `try/except` around `signal.signal()` and silently skip unsupported signals. Test on Windows explicitly. |
| **Residual Risk** | Low — SIGINT-only is sufficient for Ctrl+C. |
| **Owner** | 8A implementation |

### R-04: Thread safety in parallel downloads

| Field | Value |
|-------|-------|
| **ID** | R-04 |
| **Category** | Correctness |
| **Description** | When `parallel_max > 1`, multiple threads write to the checkpoint file, update the RunSummary, and log progress. Without proper synchronization, this could cause data corruption or race conditions. |
| **Likelihood** | Medium |
| **Impact** | High |
| **Score** | 6 ⚠️ |
| **Affected Milestone** | 8B |
| **Mitigation** | Use `threading.Lock` for checkpoint writes. `RunSummary` aggregation uses thread-safe counters (`dict` updates are atomic in CPython due to GIL, but explicit locking is safer). `logging` module is already thread-safe. Each thread creates its own `requests.Session`. All shared mutable state is protected. |
| **Residual Risk** | Low — Explicit locking plus GIL makes this safe. |
| **Owner** | 8B implementation |

### R-05: Server-side rate limiting rejects parallel requests

| Field | Value |
|-------|-------|
| **ID** | R-05 |
| **Category** | External Dependencies |
| **Description** | Some textbook servers (especially NCERT) may enforce server-side rate limits. Parallel requests could trigger HTTP 429 responses, causing downloads to fail that would have succeeded sequentially. |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Score** | 6 ⚠️ |
| **Affected Milestone** | 8B |
| **Mitigation** | Default `parallel_max` to 1 (sequential) — no behavior change unless user explicitly opts in. Provide per-board `rate_limit_rpm` config to control request rate. Document recommended parallel values (start with 2-3). The existing HTTP retry logic handles transient 429 responses. Log a clear warning when 429 is received. |
| **Residual Risk** | Low — Opt-in with sensible defaults. |
| **Owner** | 8B implementation |

### R-06: Subcommand parser breaks existing CLI invocations

| Field | Value |
|-------|-------|
| **ID** | R-06 |
| **Category** | Backward Compatibility |
| **Description** | Refactoring `main.py` to support subcommands (`edf run`, `edf validate-config`, `edf diff`) could break existing invocations like `edf --config config.yaml --dry-run`. |
| **Likelihood** | Low |
| **Impact** | High |
| **Score** | 3 |
| **Affected Milestone** | 8D |
| **Mitigation** | When no subcommand is provided, default to `"run"` with exact same argument parsing as v0.7.0. Write explicit backward-compat tests: `edf --config X --dry-run` must produce identical behavior. Positional `"run"` remains optional. All existing CLI tests (test_cli.py) must pass unchanged. |
| **Residual Risk** | Low — Explicit default subcommand preserves all existing invocations. |
| **Owner** | 8D implementation |

### R-07: PyPI package name conflict

| Field | Value |
|-------|-------|
| **ID** | R-07 |
| **Category** | Packaging |
| **Description** | The package name `edf-l1` may already be taken on PyPI, preventing publication. |
| **Likelihood** | Low |
| **Impact** | Medium |
| **Score** | 3 |
| **Affected Milestone** | 8C |
| **Mitigation** | Check PyPI availability early (before any upload). Prepare fallback names: `edf-l1-dl`, `edf-download-framework`, `edf-textbooks`. Local `pip install .` works regardless of PyPI name. |
| **Residual Risk** | Low — Fallback names available. |
| **Owner** | 8C implementation |

### R-08: Docker image size too large

| Field | Value |
|-------|-------|
| **ID** | R-08 |
| **Category** | Packaging |
| **Description** | The Docker image could be larger than expected if unnecessary files are included in the build context. |
| **Likelihood** | Low |
| **Impact** | Low |
| **Score** | 2 |
| **Affected Milestone** | 8C |
| **Mitigation** | Use `.dockerignore` to exclude tests, docs, `.git`, and build artifacts. Multi-stage build with `python:3.10-slim` base. Target ≤ 200 MB. |
| **Residual Risk** | Low — Multi-stage build and slim base keep size manageable. |
| **Owner** | 8C implementation |

### R-09: Test coverage regression

| Field | Value |
|-------|-------|
| **ID** | R-09 |
| **Category** | Quality |
| **Description** | Adding new code without corresponding tests could lower the overall coverage ratio below the 80% baseline or the 85% target. |
| **Likelihood** | Low |
| **Impact** | Medium |
| **Score** | 3 |
| **Affected Milestone** | All |
| **Mitigation** | CI coverage gate enforced at ≥85%. New modules have ≥90% coverage target. All existing tests must pass unchanged. Coverage is checked on every PR. |
| **Residual Risk** | Low — Automated gate prevents regression. |
| **Owner** | All milestones |

### R-10: Release schedule slippage

| Field | Value |
|-------|-------|
| **ID** | R-10 |
| **Category** | Planning |
| **Description** | 4 weeks is an aggressive target. Unexpected issues (especially in 8A checkpoint or 8B parallel downloads) could cause slippage. |
| **Likelihood** | Medium |
| **Impact** | Low |
| **Score** | 3 |
| **Affected Milestone** | All |
| **Mitigation** | Milestones are independent — if 8A slips, 8C (packaging) can begin. P2 items can be deferred. Buffer time is built into each week (5 days allocated, ~4 days of actual work). |
| **Residual Risk** | Low — Flexible milestone structure absorbs delays. |
| **Owner** | Project lead |

### R-11: Descriptor key collision across runs

| Field | Value |
|-------|-------|
| **ID** | R-11 |
| **Category** | Correctness |
| **Description** | If the checkpoint key (derived from board, filename, URL) is not unique enough, different runs could share checkpoint state, causing incorrect skip behavior. |
| **Likelihood** | Low |
| **Impact** | Medium |
| **Score** | 3 |
| **Affected Milestone** | 8A |
| **Mitigation** | Key = `f"{board}:{url}"` — URL is unique per textbook. Include a run_id prefix in the checkpoint file name (`.edf/checkpoint_{run_id}.json`) to isolate runs. Alternatively, clear checkpoint on successful completion of all descriptors. |
| **Residual Risk** | Low — URL-based keys are unique per textbook. |
| **Owner** | 8A implementation |

### R-12: Progress display garbled in parallel mode

| Field | Value |
|-------|-------|
| **ID** | R-12 |
| **Category** | User Experience |
| **Description** | When multiple downloads run in parallel, progress updates from different threads could interleave, producing garbled output. |
| **Likelihood** | Medium |
| **Impact** | Low |
| **Score** | 3 |
| **Affected Milestone** | 8B |
| **Mitigation** | Route all progress through the `logging` module (which is thread-safe and serializes output). In parallel mode, emit summary progress (e.g., "3/10 completed, 2 in progress") rather than per-file interleaving. The `rich` library can be used for structured progress bars if desired (already a dependency). |
| **Residual Risk** | Low — Logging module handles serialization. |
| **Owner** | 8B implementation |

---

## Risk Summary

### By Likelihood

| Likelihood | Count | IDs |
|-----------|-------|-----|
| Low | 6 | R-01, R-06, R-07, R-08, R-09, R-11 |
| Medium | 6 | R-02, R-03, R-04, R-05, R-10, R-12 |

### By Impact

| Impact | Count | IDs |
|--------|-------|-----|
| High | 2 | R-04 (thread safety), R-06 (CLI compat) |
| Medium | 5 | R-01, R-05, R-07, R-09, R-11 |
| Low | 5 | R-02, R-03, R-08, R-10, R-12 |

### By Score

| Score | Level | Count | IDs |
|-------|-------|-------|-----|
| 6+ | Elevated | 2 | R-04, R-05 |
| 3-5 | Moderate | 9 | R-01, R-02, R-03, R-06, R-07, R-09, R-10, R-11, R-12 |
| 1-2 | Low | 1 | R-08 |

### Elevated Risks (Score ≥ 6)

| ID | Risk | Likelihood | Impact | Primary Mitigation |
|----|------|-----------|--------|-------------------|
| R-04 | Thread safety in parallel downloads | Medium | High | `threading.Lock` for checkpoint; logging module is thread-safe |
| R-05 | Server rate limiting rejects parallel requests | Medium | Medium | Default sequential; opt-in parallel; per-board RPM config |

Both elevated risks are well-understood problems with standard mitigations (explicit locking, opt-in behavior with conservative defaults).

---

## Comparison with Rejected Risk Register

| Dimension | Rejected Risk Register | Revised Risk Register |
|-----------|----------------------|----------------------|
| Total risks | 15 | 12 |
| High-impact risks | 6 | 2 |
| Elevated (score ≥ 6) | 6+ | 2 |
| Categories | Security, Performance, Deployment, Extensibility, Operational | Reliability, Correctness, Platform, Backward Compat, Packaging, Quality |
| Highest risk | "Async refactor introduces nondeterminism" | "Thread safety in parallel downloads" |
| Risk profile | High (unproven technologies: async, K8s, Vault, OTel) | Low (evolutionary, proven patterns) |
| New technology risks | OpenTelemetry integration, Vault integration, async refactor | None — all patterns are standard Python |
| Infrastructure risks | Container vulnerabilities, K8s misconfiguration, supply chain | Docker image size, PyPI name conflict |

The revised risk register has **significantly lower risk exposure** because it avoids introducing unproven technologies and stays within the well-understood Python ecosystem.

---

## Risk Monitoring

During Phase 8 development, risks are monitored as follows:

1. **Per-PR review:** Each PR includes a risk checklist — does this change touch any elevated-risk area?
2. **Per-milestone review:** At the end of each milestone, reassess all risks and update likelihood/impact based on implementation experience.
3. **Test coverage gate:** Automated CI gate catches R-09 (coverage regression) immediately.
4. **Backward-compat tests:** R-06 is mitigated by requiring all existing tests to pass unchanged.

---

*End of PHASE8_REVISED_RISK_REGISTER.md*
