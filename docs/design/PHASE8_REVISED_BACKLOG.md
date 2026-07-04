# Phase 8 Revised Backlog — EDF-L1 v0.8.0

> **Status:** Draft for Approval
> **Date:** 2026-07-04
> **Baseline:** v0.7.0
> **Target:** v0.8.0

---

## Priority Definitions

| Priority | Meaning | Criteria |
|----------|---------|----------|
| **P0** | Must-have for release | Without this, the release is blocked. Core reliability or packaging. |
| **P1** | Should-have | Significantly improves user experience. Would regret not including. |
| **P2** | Nice-to-have | Valuable improvement but can defer to a future minor release. |

---

## Backlog Items

### P0 — Must-Have

| ID | Title | Milestone | Business Value | Technical Value | Complexity | Risk | Dependencies | Est. Days |
|----|-------|-----------|---------------|----------------|-----------|------|-------------|-----------|
| **B-01** | Checkpoint Manager | 8A | High — Users never lose download progress on interrupt | High — Foundation for resume and graceful shutdown | Medium | Low — Standard JSON persistence | None | 2 |
| **B-02** | Resume interrupted downloads (`--resume`) | 8A | High — Key reliability improvement for large downloads | High — Completes checkpoint value | Medium | Low — Reads checkpoint, skips completed | B-01 | 1 |
| **B-03** | Graceful Ctrl+C handling | 8A | High — Current behavior may corrupt temp files | High — Signal handling is fundamental to CLI tools | Medium | Medium — Windows signal handling edge cases | B-01 | 1 |
| **B-04** | Progress tracking per file | 8B | High — Users need to see download progress for large PDFs | Medium — Callback infrastructure useful for parallel mode | Low | Low | None | 1.5 |
| **B-05** | Parallel downloads (optional) | 8B | High — Speed improvement for bulk downloads | Medium — ThreadPoolExecutor is well-understood | Medium | Medium — Thread safety in checkpoint, server rate limits | B-01 | 1.5 |
| **B-06** | PyPI packaging | 8C | High — Makes EDF-L1 installable via pip | High — Standard distribution mechanism | Low | Low — Standard Python packaging | None | 1.5 |
| **B-07** | Dockerfile | 8C | Medium — Enables containerized deployment | Medium — Reproducible environment | Low | Low | B-06 | 1 |
| **B-08** | CI improvements (coverage gate, matrix) | 8C | High — Automated quality gate prevents regression | High — Ensures reliability of release process | Low | Low | None | 1.5 |

### P1 — Should-Have

| ID | Title | Milestone | Business Value | Technical Value | Complexity | Risk | Dependencies | Est. Days |
|----|-------|-----------|---------------|----------------|-----------|------|-------------|-----------|
| **B-09** | Per-board rate limiting | 8B | Medium — Prevents overwhelming textbook servers | Medium — Config-driven rate control | Low | Low | None | 1 |
| **B-10** | Manifest diff (`edf diff`) | 8D | Medium — Users can see what changed between runs | Medium — Useful for audit trails | Low | Low | None | 1.5 |
| **B-11** | JSON output mode (`--json`) | 8D | Medium — Enables integration with other tools | Medium — Machine-readable output | Low | Low | None | 1 |
| **B-12** | `validate-config` subcommand | 8D | Medium — Quick way to check config without running | Medium — Separates validation from execution | Low | Low | None | 0.5 |
| **B-13** | Config validation extensions (V11-V14) | 8A | Low — Prevents invalid new config values | High — Catches config errors early | Low | Low | None | 0.5 |
| **B-14** | Checkpoint expiry | 8A | Low — Prevents stale checkpoints from blocking | Medium — Clean state management | Low | Low | B-01 | 0.5 |
| **B-15** | `--progress` CLI flag | 8B | Low — Users can disable progress if desired | Low — Config gating | Low | Low | B-04 | 0.5 |

### P2 — Nice-to-Have

| ID | Title | Milestone | Business Value | Technical Value | Complexity | Risk | Dependencies | Est. Days |
|----|-------|-----------|---------------|----------------|-----------|------|-------------|-----------|
| **B-16** | Download speed benchmarking | 8B | Low — Useful for performance testing | Medium — Quantifies improvement from parallel mode | Medium | Low | B-05 | 0.5 |
| **B-17** | Manifest history (keep N snapshots) | 8D | Low — Users can diff against any previous run | Low — Simple rotation | Low | Low | B-10 | 0.5 |
| **B-18** | Rich progress display (spinners, tables) | 8B | Low — Better UX | Low — Leverages existing `rich` dependency | Low | Low | B-04 | 0.5 |
| **B-19** | Config schema documentation | 8D | Low — Helps users write valid configs | Low — Generated from defaults | Low | Low | B-12, B-13 | 0.5 |

---

## Effort Summary

| Priority | Item Count | Total Days |
|----------|-----------|------------|
| P0 | 8 | 11.0 |
| P1 | 7 | 5.5 |
| P2 | 4 | 2.0 |
| **Total** | **19** | **18.5 days (~4 weeks)** |

---

## Milestone Allocation

### Phase 8A — Reliability (Week 1)

| ID | Title | Priority | Days |
|----|-------|----------|------|
| B-01 | Checkpoint Manager | P0 | 2 |
| B-02 | Resume interrupted downloads | P0 | 1 |
| B-03 | Graceful Ctrl+C handling | P0 | 1 |
| B-13 | Config validation extensions (V11-V14) | P1 | 0.5 |
| B-14 | Checkpoint expiry | P1 | 0.5 |
| | **Subtotal** | | **5 days** |

### Phase 8B — Performance (Week 2)

| ID | Title | Priority | Days |
|----|-------|----------|------|
| B-04 | Progress tracking per file | P0 | 1.5 |
| B-05 | Parallel downloads (optional) | P0 | 1.5 |
| B-09 | Per-board rate limiting | P1 | 1 |
| B-15 | `--progress` CLI flag | P1 | 0.5 |
| B-16 | Download speed benchmarking | P2 | 0.5 |
| B-18 | Rich progress display | P2 | 0.5 |
| | **Subtotal** | | **5.5 days** |

### Phase 8C — Packaging (Week 3)

| ID | Title | Priority | Days |
|----|-------|----------|------|
| B-06 | PyPI packaging | P0 | 1.5 |
| B-07 | Dockerfile | P0 | 1 |
| B-08 | CI improvements | P0 | 1.5 |
| | **Subtotal** | | **4 days** |

### Phase 8D — Developer Experience (Week 4)

| ID | Title | Priority | Days |
|----|-------|----------|------|
| B-10 | Manifest diff | P1 | 1.5 |
| B-11 | JSON output mode | P1 | 1 |
| B-12 | `validate-config` subcommand | P1 | 0.5 |
| B-17 | Manifest history | P2 | 0.5 |
| B-19 | Config schema documentation | P2 | 0.5 |
| | **Subtotal** | | **4 days** |

---

## Risk vs. Value Matrix

```
         High Business Value
              │
     B-01 ●  │  ● B-05     ● B-06
     B-02 ●  │  ● B-04
     B-03 ●  │
              │
─────────────┼─────────────── Low Complexity
              │
     B-09 ●  │              ● B-16
     B-10 ●  │  ● B-11
     B-12 ●  │
              │
         Low Business Value

         Low Risk ────────── High Risk
```

All P0 items cluster in the high-value, low-risk quadrant — confirming the revised plan is appropriately scoped.

---

## Scope Exclusions

The following items were considered but explicitly excluded from Phase 8:

| Excluded Item | Reason | Future Consideration |
|---------------|--------|---------------------|
| REST API | Not justified for a CLI tool | Never (out of scope for EDF-L1) |
| Async runtime (asyncio) | Not needed; ThreadPoolExecutor suffices | Phase 9 if justified |
| Database (SQLite) | manifest.json serves this role | Never (over-engineering) |
| Incremental checksum verification | Checkpoint already covers this | Phase 9 |
| Download scheduling / cron | OS-level concern, not application | Never |
| Web UI | Out of scope for CLI tool | Never |
| Multi-language i18n | Not needed for English-language tool | Never |
| Plugin marketplace | Adapter registry already exists and is sufficient | Never |
| Streaming validation (validate during download) | Adds complexity; post-download validation is sufficient | Phase 9 |

---

## Comparison with Rejected Backlog

| Dimension | Rejected Backlog | Revised Backlog |
|-----------|-----------------|----------------|
| Total items | 41 | 19 |
| P0 items | ~15 | 8 |
| Story points | 165 | ~50 |
| Enterprise features | SecretProvider, MetricsLayer, PluginRegistry, API Gateway | None |
| Infrastructure items | Kubernetes, Helm, SBOM, artifact signing | Dockerfile (optional) |
| Test infra | Chaos testing, security scanning, benchmark regression | Coverage gate |
| Estimated effort | 21 weeks | 4 weeks |

---

*End of PHASE8_REVISED_BACKLOG.md*
