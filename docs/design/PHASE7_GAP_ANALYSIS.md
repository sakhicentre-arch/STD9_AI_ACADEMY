# Phase 7 — Gap Analysis

> **Purpose:** A complete, evidence-grounded catalogue of the gaps between the
> **documented** EDF-L1 product (per `README.md`, `config.yaml.example`, and
> the inline docstrings) and the **actual** code at the Phase 6 release
> baseline (commit `ef3ce2f`, v0.6.0). Every gap below is classified by
> severity and traced to the source line, behaviour, or test that proves it.
>
> **Companion documents:**
> - [`docs/architecture/PHASE7_ARCHITECTURE.md`](../architecture/PHASE7_ARCHITECTURE.md)
> - [`docs/design/PHASE7_TECHNICAL_DESIGN.md`](../design/PHASE7_TECHNICAL_DESIGN.md)
>
> **Constraints honoured (Milestone 1):** This is analysis only. It proposes
> no changes to production code, tests, the README, or git history. All
> "Recommended solution" entries are *specifications* for later milestones.

---

## Severity Classification Scheme

Every gap is labelled with exactly one of:

| Severity | Definition |
|----------|------------|
| **Critical** | The framework cannot be used for its documented purpose as-is, or it appears to succeed while doing nothing. Blocks all downstream verification. |
| **High** | The documented contract is violated or a key feature is non-functional, but a knowledgeable user can work around it. |
| **Medium** | Correct in the common case but fragile, misleading, or carrying latent defects (e.g. silent key drift, dead parameters). |
| **Low** | Cosmetic, informational, or a deliberate deferral that does not affect correctness of the core path. |

---

## 1. Executive Summary

The EDF-L1 core pipeline — adapters, registry, downloader, storage, manifest,
and logging — is **implemented, stable, and unit-tested**. The Phase 6 release
delivered genuinely board-agnostic orchestration with GSEB and NCERT
adapters, content-addressed atomic storage, checksum-driven dedup, and a
manifest subsystem with atomic persistence.

**However, the framework is currently unusable from its own documented entry
point.** Two structural breaks in the call graph prevent the end-to-end path
from ever running:

1. **`ConfigLoader` is a placeholder** (`src/edf/core/config.py`): it never
   reads `config.yaml` and never validates it. It silently returns a
   hardcoded `{"version": "1.0"}`.
2. **`main.py` is a bootstrap stub**: it prints `"EDF-L1 Bootstrap Ready"`
   and exits 0 without constructing or invoking the orchestrator.

Because these two components are the **single points of entry**, their
absence is not merely a missing feature — it is the reason the entire
documented user journey (`cp config.yaml.example config.yaml; python
main.py`) produces a *successful-looking no-op* rather than a real run.

A user following the README today will see "Bootstrap Ready" and believe the
pipeline executed, while in reality **nothing was loaded, validated, or
downloaded**. This silent no-op masquerading as success is the single most
dangerous defect in the codebase and is the dominant driver of Phase 7
priorities.

Beyond the two entry breaks, this analysis catalogues **13 additional
defects** spanning configuration, runtime behaviour, validation, testing,
and documentation. Of the total 15 gaps:

- **3 Critical** (G1, G2, G3) — the entry-point breaks + the non-existent CLI flags.
- **3 High** (G4, G7, G8) — untested E2E path, doc/code drift, dry-run not enforced.
- **5 Medium** (G5, G9, G10, G11, G12) — dead plumbing, key drift, stale docstrings, missing CI, exception leakage.
- **4 Low** (G6, G13, G14, G15) — deferrals, polish, non-blocking.

**Headline conclusion:** The work to convert EDF-L1 from
"components-verified" to "system-verified" is **small, well-bounded, and
low-risk** — because the stable core already consumes a plain `config`
dict. Phase 7 is **completion, not redesign.** The critical path is
ConfigLoader → CLI → integration test → documentation, in that order.

---

## 2. Current Architecture Gaps

These are *structural* defects in the call graph — links that the
architecture intends but that are broken or missing. Per-gap detail follows
in subsequent sections; this section gives the structural overview.

| # | Gap | Severity | Layer | Where proven |
|---|-----|----------|-------|--------------|
| **G1** | `ConfigLoader` is a placeholder; `config.yaml` is never read or validated. | **Critical** | Config | `config.py:130-160` |
| **G2** | `main.py` is a bootstrap stub; the orchestrator is never invoked. | **Critical** | Entry point | `main.py:10-20` |
| **G3** | Documented CLI flags (`--dry-run`, `--board`, `--verify-only`) do not exist. | **Critical** | Entry point | `main.py:10-20`; README L188-191 |
| **G8** | `dry_run` is read from config but never honoured at runtime. | **High** | Orchestration | `pipeline.py`, `downloader.py` (no `dry_run` refs) |

> **Why these are architectural, not feature-level:** The downstream core
> (registry, adapters, downloader, storage, manifest, utils, logging) is
> intact and contract-stable. The call graph is broken at exactly the two
> entry edges (loader + CLI) plus one internal propagation gap (dry-run).
> Closing these three restores the intended end-to-end path without touching
> the frozen core.

### G1 — `ConfigLoader` placeholder (Critical)

- **Current implementation:** `ConfigLoader.__init__` calls `self._load()`
  then `self._validate()`. `_load()` (`config.py:130-143`) has the real
  YAML read **commented out** and instead executes
  `self._raw = {"version": "1.0"}  # Placeholder for Phase 1 bootstrap`.
  `_validate()` (`config.py:145-160`) is a `pass` stub with a `TODO`.
  The typed accessors (`config`, `general`, `download`, `content_root`,
  `is_dry_run`, `get_textbooks`, …) **are** implemented, but they read the
  placeholder dict, not a real file.
- **Why it is a problem:** Any component that depends on `ConfigLoader` for
  its configuration receives `{"version": "1.0"}` regardless of the actual
  `config.yaml` on disk. Board sections, textbooks, download limits,
  validation thresholds, and templates are all invisible to the running
  system. The user's authored configuration is silently discarded.
- **Risk if left unresolved:** Every board/textbook directive is ignored.
  The pipeline, if ever invoked, would run with empty descriptors and
  produce a "nothing to do" summary that *looks* healthy. Combined with G2,
  this is the silent-no-op failure mode (Risk R1).
- **Recommended solution:** Implement `_load()` to read YAML via
  `yaml.safe_load` (already a declared dependency) with `FileNotFoundError`
  on missing path and `ConfigValidationError` on malformed YAML; implement
  `_validate()` per the rule set V1–V10 in the Technical Design §2.2.2.
  Do **not** change accessor signatures (frozen public surface).
- **Dependencies:** None. This is the root of the critical path.
- **Estimated effort:** **Small–Medium** (~1–2 dev-days). Logic is fully
  specified in the Technical Design; CL-T1…CL-T11 test matrix is pre-written.

### G2 — `main.py` bootstrap stub (Critical)

- **Current implementation:** `main()` (`main.py:10-20`) prints
  `"EDF-L1 Bootstrap Ready"` and `return 0`. It imports only `sys`; it does
  not import `ConfigLoader`, `EDFLogger`, or `PipelineOrchestrator`, and
  never constructs or calls them.
- **Why it is a problem:** The documented entry point (`python main.py`,
  bound as the `edf` console script in `pyproject.toml:27`) does nothing
  functional. The entire implemented pipeline is unreachable from the user
  interface that the README and packaging advertise.
- **Risk if left unresolved:** The framework cannot be run by its intended
  users. Worse, exit code `0` and the "Ready" message imply success,
  reinforcing the silent-no-op trap (R1).
- **Recommended solution:** Rewrite `main()` as a thin composition root
  (Technical Design §3.4): parse args → construct `ConfigLoader` + `EDFLogger`
  + `PipelineOrchestrator` → `initialize()` → `run()` → `shutdown()` → map
  exit code. Extract a `build_orchestrator(args)` helper for testability.
  Preserve the `edf = "main:main"` binding.
- **Dependencies:** **G1** (needs a real loader) and **G3** (flag parsing).
- **Estimated effort:** **Small** (~1 dev-day) once G1 lands.

### G3 — Documented CLI flags do not exist (Critical)

- **Current implementation:** `main.py` accepts no arguments. README L188–191
  documents `python main.py`, `python main.py --dry-run`,
  `python main.py --board GSEB`, and `python main.py --verify-only`. None of
  these flags are parsed or honoured anywhere in the codebase.
- **Why it is problem:** The documented CLI surface is fictional. A user
  passing `--dry-run` today gets the bootstrap print (the flag is silently
  ignored), so a "dry-run" can give false confidence that a destructive run
  was simulated.
- **Risk if left unresolved:** Users rely on flags that do nothing;
  `--dry-run` in particular failing silently is a data-safety hazard (a user
  may believe they dry-ran a large batch before committing to a real run).
- **Recommended solution:** Add `--config`, `--dry-run`, `--board`,
  `--verify-only` via `argparse` per Technical Design §3.3, with the
  documented exit-code mapping (0 success / 1 partial / 2 fatal).
- **Dependencies:** **G2** (entry point), **G1** (loader), **G8** (dry-run
  must actually be honoured for `--dry-run` to be truthful).
- **Estimated effort:** **Medium** (~2 dev-days). `--config` is trivial;
  `--board` (synthetic `boards` section) and `--verify-only` (new orchestrator
  path) are the substantive parts.

### G8 — `dry_run` not propagated (High)

- **Current implementation:** `ConfigLoader.is_dry_run` exists
  (`config.py:108-110`) and reads `general.dry_run`. A grep of
  `pipeline.py` and `downloader.py` for `dry_run`/`is_dry_run` returns
  **zero matches** — nothing downstream consults the flag.
- **Why it is a problem:** A config with `dry_run: true` still downloads
  files. The flag is a documented no-op at runtime, defeating its entire
  purpose and creating a data-safety false sense.
- **Risk if left unresolved:** `--dry-run` (G3) cannot be implemented
  truthfully. Users cannot safely simulate runs. Risk R (data-write during
  what should be a plan-only mode).
- **Recommended solution:** Two-layer guard per Technical Design §4: (1)
  orchestrator short-circuits `download_pipeline.run()` when dry-run,
  producing a clean "skipped" summary; (2) descriptor-level
  `_process_descriptor` checks a `dry_run` flag as defence-in-depth and
  returns `{"status":"skipped","reason":"dry_run"}` without touching the
  network or filesystem.
- **Dependencies:** **G1** (flag must come from a real loader).
- **Estimated effort:** **Small** (~1 dev-day).

---

## 3. Placeholder Implementations

Modules whose body is a deliberate stub, marked `TODO`, or returns a
hardcoded stand-in instead of real behaviour.

### G1 (restated) — `ConfigLoader._load()` / `_validate()` (Critical)

See §2 G1. `_load()` returns a hardcoded dict; `_validate()` is `pass`.
*This is the highest-impact placeholder in the codebase* because it sits on
the critical entry path.

### G6 — `get_page_count()` is a `TODO` returning `None` (Low)

- **Current implementation:** `utils/pdf.py:67-82` defines
  `get_page_count()` whose body is `# TODO: Implement page count detection.`
  followed by `return None`. Its docstring states it "requires PDF parsing
  library (e.g., PyMuPDF, pypdf)."
- **Why it is a problem:** A grep of `src/` and `tests/` shows
  `get_page_count` has **zero call sites**. It is an orphan — nothing reads
  its result, so the `None` return currently causes no runtime harm.
- **Risk if left unresolved:** Negligible *today* (unused). The latent risk
  is that a future feature (e.g. richer `ValidationResult`, manifest page
  counts) calls it expecting a real number and silently records `None`.
- **Recommended solution:** Phase 7 **decision, not implementation** (see
  Technical Design §8 Non-Goals). Either (a) delete the orphan to remove the
  false promise, or (b) keep it but mark its docstring unambiguous and gate
  any future caller on a non-`None` check. Full implementation requires a
  PDF-library dependency decision and is explicitly deferred out of Phase 7.
- **Dependencies:** None for the decision; a dependency choice
  (`pypdf` vs `PyMuPDF`) for any implementation.
- **Estimated effort:** **Low** — minutes to delete/mark; deferred for real
  implementation.

### G2 (restated) — `main()` stub (Critical)

See §2 G2. `main()` prints and returns rather than doing work. It is the
entry-point equivalent of the `_load()` placeholder.

---

## 4. Runtime Gaps

Defects in *runtime behaviour* — code paths that execute incorrectly or not
at all, given a valid config.

### G8 (restated) — dry-run not enforced (High)

See §2 G8. The most material runtime gap: a flag is read but never acted
upon, so `dry_run: true` still writes files to disk.

### G5 — `http_client` is plumbed through but never used (Medium)

- **Current implementation:** `BaseAdapter.__init__(config, http_client=None)`
  (`base.py:55-64`), `GSEBAdapter.__init__` (`gseb.py:54-62`),
  `NCERTAdapter.__init__` (`ncert.py:95-103`), and
  `AdapterRegistry.create(..., http_client=None)` (`registry.py:148-170`)
  all accept and forward `http_client`. Yet every adapter docstring states
  it is *"currently unused"* / *"reserved for future use"* — URL checks
  instead call `utils.http` functions directly.
- **Why it is a problem:** Dead, opinionated plumbing. It implies an
  injection seam (testability/mocking of HTTP) that does not actually exist,
  misleading anyone reading or extending the adapter contract. It also
  widens the public surface of a frozen ABC for no behavioural gain.
- **Risk if left unresolved:** Continued confusion about where HTTP
  behaviour is injected; a contributor may wire into `http_client` expecting
  it to take effect and find pre-flight still hits the network via utils.
  Low correctness risk; moderate clarity/maintainability risk.
- **Recommended solution:** Phase 7 **decision** (Technical Design §8):
  either (a) remove `http_client` from the adapter/registry signatures
  (clean, but touches the ABC contract — evaluate against the "frozen core"
  principle), or (b) actually wire it into pre-flight checks so the seam is
  real and testable. Recommended: document the decision and defer to a
  hardening milestone rather than half-implement.
- **Dependencies:** None for the decision.
- **Estimated effort:** **Low** to decide; **Medium** if wiring is chosen.

### G10 — Exit-code / exception mapping is undocumented at the boundary (Medium)

- **Current implementation:** `RunSummary.exit_code` encodes success/partial/
  fatal semantics (`models/data.py`), and the Technical Design maps them to
  CLI exit codes (0/1/2). But there is currently **no production code path**
  that translates a raised `ConfigValidationError` or `FileNotFoundError`
  into exit code `2` — because `main.py` never runs the pipeline (G2).
- **Why it is a problem:** The mapping exists by design intent only; until
  G2/G3 land, a misconfiguration cannot produce the documented exit 2. This
  is a latent runtime gap that will materialise the moment the CLI is wired.
- **Risk if left unresolved:** A future CLI that does not catch
  `ConfigValidationError` will surface a Python traceback (exit 1) instead
  of a clean, documented exit 2 — bad UX and a false "partial failure" signal.
- **Recommended solution:** The CLI composition root must wrap loader
  construction in `try/except (FileNotFoundError, ConfigValidationError)`
  and return `2` (Technical Design §3.4). Specify, do not implement, here.
- **Dependencies:** **G2**, **G3**.
- **Estimated effort:** **Trivial** (a `try/except` block), folded into the
  CLI milestone.

---

## 5. Configuration Gaps

Defects in how configuration is authored, named, and consumed.

### G9 — Chunk-size key mismatch (`chunk_size` vs `chunk_size_bytes`) (Medium)

- **Current implementation:** `downloader.py:209` reads
  `self._download_cfg.get("chunk_size", 8192)`. The config template
  (`config.yaml.example:18`) and all docstrings name the key
  `chunk_size_bytes`. So the user-configured value is **never read**; the
  downloader always falls back to the `8192` default.
- **Why it is a problem:** A latent, silent defect. A user who tunes
  `chunk_size_bytes` to control memory/network behaviour sees no effect and
  no error. This is the canonical "key drift" trap.
- **Risk if left unresolved:** Any chunk-size tuning is a no-op; debugging
  is misdirected. Once G1 lands (real loader), this becomes a *live* silent
  failure rather than a dormant one.
- **Recommended solution:** Canonicalise at load time (Technical Design
  V10): `ConfigLoader._validate()` accepts **either** `chunk_size` **or**
  `chunk_size_bytes` and normalises to the key the downloader reads, so the
  configured value is honoured without changing downloader code.
- **Dependencies:** **G1** (normalisation belongs in the loader).
- **Estimated effort:** **Small** (alias logic + one test).

### G1-validation (restated) — No schema/range validation (Critical)

See §2 G1. The absence of `_validate()` means types, required fields,
template placeholders, and numeric ranges are unchecked. A `download.timeout_seconds: "abc"`
or a `gseb.textbooks[0]` missing `url` would flow through silently until it
crashed deep in the pipeline with an opaque error. Rules V1–V10 (Technical
Design §2.2.2) close this.

### G11 — Config defaults are duplicated across layers (Medium)

- **Current implementation:** Defaults like `"./CONTENT"`, `".edf"`, `3`
  retries, `120` timeout, `8192` chunk, `10240` min-size appear **both** as
  `.get(..., default)` literals inside the consumers *and* inside
  `ConfigLoader` accessors (see Architecture §3.3 table). There is no single
  source of truth.
- **Why it is a problem:** If a default changes in one place, the other
  drifts. Two components reading the "same" key can disagree on the default,
  producing subtle behavioural divergence when the key is absent from YAML.
- **Risk if left unresolved:** Default drift over time; harder reasoning
  about "what happens when this key is missing."
- **Recommended solution:** Make `ConfigLoader` (post-validation) the single
  source of truth for defaults; document that consumers may rely on the
  loader having populated them. Phase 7 *documents* this; full removal of
  consumer-level `.get` fallbacks is a hardening task that must not change
  observable behaviour.
- **Dependencies:** **G1**.
- **Estimated effort:** **Medium** (mechanical but touches many call sites;
  defer most to a hardening milestone).

---

## 6. CLI Gaps

### G2 (restated) — No CLI entry (Critical)

See §2 G2. `main.py` is a stub; the orchestrator is unreachable.

### G3 (restated) — No documented flags (Critical)

See §2 G3. `--dry-run`, `--board`, `--verify-only`, and `--config` are
absent.

### G12 — No `--config` path argument / no console-script verification (Medium)

- **Current implementation:** `pyproject.toml:27` declares
  `edf = "main:main"`, but `main()` takes no `argv` and accepts no
  `--config`. There is no test verifying that the installed `edf` console
  script resolves and runs.
- **Why it is a problem:** The packaged entry point is unverified; a
  packaging regression (e.g. wrong module path after a refactor) would only
  be caught by an end user.
- **Risk if left unresolved:** The "install and run" path is untested.
- **Recommended solution:** `main(argv=None)` signature (testable); add a
  smoke test that imports `main` and calls it with a known-good temp config
  (part of the Phase 7C integration milestone).
- **Dependencies:** **G2**, **G3**, **G4**.
- **Estimated effort:** **Small** (folded into the CLI + integration milestones).

---

## 7. Validation Gaps

### G1-validation (restated) — No config validation (Critical)

See §5. `_validate()` is `pass`. The rule set V1–V10 must enforce: schema
version, `general` mapping, non-empty `content_root`, numeric types/ranges,
per-board `REQUIRED_FIELDS` (copied verbatim from `gseb.py`/`ncert.py`),
NCERT template placeholders, and the chunk-size alias.

### G6 (restated) — PDF page-count validation unavailable (Low)

See §3. `get_page_count()` returns `None`; there is therefore no PDF-content
validation beyond header/size/MIME. This is an accepted deferral, not a
correctness bug, but it bounds the depth of `ValidationResult`.

### G13 — Validation surface is not documented as a contract (Low)

- **Current implementation:** `validate_pdf_header`, `validate_pdf_size`,
  `validate_mime_type` exist and are exercised; but the *combination* of
  checks that constitutes "a valid PDF" (header ∧ size ∧ MIME, with
  descriptor-level `expected_size`/`expected_sha256` overrides) is not
  written down in one place.
- **Why it is a problem:** Contributors cannot easily see the full
  validation contract without reading `downloader.py` validation internals.
- **Risk if left unresolved:** Minor; documentation-only.
- **Recommended solution:** Document the composed validation contract in the
  Phase 7D documentation update (deferred, out of code scope).
- **Dependencies:** None.
- **Estimated effort:** **Low** (doc-only).

---

## 8. Testing Gaps

### G4 — No end-to-end test through a real `ConfigLoader` (High)

- **Current implementation:** The closest test,
  `tests/test_multiboard_integration.py:90-97`, builds a
  `SimpleNamespace(config=..., content_root=..., edf_metadata_dir=...,
  is_force_overwrite=...)` as a **stand-in** for `ConfigLoader` and stubs
  `DownloadPipeline.run`. No test in the suite imports or instantiates the
  real `ConfigLoader`, and no test loads a real `config.yaml`.
- **Why it is a problem:** The intended lifecycle (load YAML → validate →
  inject into orchestrator → run → store on disk) is **never exercised**.
  The framework is "components-verified" but not "system-verified." G1/G2/G3
  could ship broken and the test suite would stay green.
- **Risk if left unresolved:** Regressions in the entry path are invisible.
  This is the gap that, once closed, converts the release from
  "unit-tested" to "integration-verified."
- **Recommended solution:** Add a Phase 7C integration test (Technical
  Design §5): write a temp `config.yaml`, serve a small valid PDF via the
  local-HTTP fixture pattern from `test_integration_staged.py:47-70`,
  construct the real `ConfigLoader`, run `PipelineOrchestrator.run()`, and
  assert exit 0, one file under `CONTENT/<board>/`, one manifest entry, one
  checksum registered, `RunSummary.succeeded == 1`.
- **Dependencies:** **G1, G2, G3, G8** (the path under test must first exist).
- **Estimated effort:** **Medium** (~1.5 dev-days).

### G14 — No test for the documented CLI flags (Low until CLI exists)

- **Current implementation:** No CLI exists, so no CLI tests. The Technical
  Design pre-specifies CLI-T1…CLI-T6 (exit codes, dry-run no-write,
  `--board` scoping, `--verify-only`).
- **Why it is a problem:** Once G3 lands, the flag behaviours (especially
  `--dry-run` producing zero writes, and `--verify-only` not downloading)
  must be asserted or they will silently regress.
- **Risk if left unresolved:** Flag semantics drift; `--dry-run` could
  silently start writing.
- **Recommended solution:** Implement CLI-T1…CLI-T6 alongside the CLI
  milestone (Phase 7B/7C).
- **Dependencies:** **G3**.
- **Estimated effort:** **Small–Medium** (folded into the CLI milestone).

### G15 — No CI pipeline / coverage gating (Low)

- **Current implementation:** `pyproject.toml:41-42` configures coverage
  sources, but there is no CI workflow file (no `.github/workflows/`) and no
  coverage gate. The suite (~214 tests across 7 files) runs only locally.
- **Why it is a problem:** Green-on-my-machine risk; regressions are not
  caught on push/PR.
- **Risk if left unresolved:** Future Phase 7 code can land unverified on
  shared branches.
- **Recommended solution:** Add a minimal CI workflow running `pytest` (+ the
  coverage gate) on push/PR, as part of Phase 7C/7D. Out of Milestone 1
  scope to implement.
- **Dependencies:** None strictly; benefits from G4 existing.
- **Estimated effort:** **Low** (~half a dev-day).

---

## 9. Documentation Gaps

### G7 — README claims "Production ready" and documents a non-existent CLI (High)

- **Current implementation:** `README.md:5` states *"Phase 6 complete — ✅
  **Production ready** for multi-board sources."* Lines 188–191 document
  `python main.py`, `--dry-run`, `--board GSEB`, and `--verify-only` as if
  they exist. `main.py` is a stub; none of these work.
- **Why it is a problem:** Direct, verifiable documentation/code mismatch.
  Users are misled into believing the documented entry point works and that
  the product is production-ready. This is the most user-visible defect in
  the project.
- **Risk if left unresolved:** Eroded trust; users attempt documented
  commands that silently no-op (compounding R1). A "production ready" claim
  on an entry point that does not run is a correctness-of-claims risk.
- **Recommended solution:** Phase 7D documentation update (constraint: do
  **not** edit docs in Milestone 1). Once G2/G3 land, align the README: (a)
  update status to reflect actual CLI availability; (b) correct/confirm the
  command examples against the implemented flags; (c) remove or qualify
  "Production ready" until G4 (E2E test) passes. The README must describe
  the code, not aspirational behaviour.
- **Dependencies:** **G2, G3, G4** (docs must describe shipped, verified
  behaviour).
- **Estimated effort:** **Small** (doc-only; ~half a dev-day), but only after
  the CLI and E2E test exist.

### Stale docstrings (Medium, folded into G11/G5)

- `utils/http.create_session` docstring is stale (it returns a real
  `requests.Session`; Architecture §1.1). `get_page_count`'s docstring
  promises future behaviour. Adapter `http_client` docstrings describe an
  injection seam that does not function (G5). These are correctness-of-prose
  defects that should be reconciled in the Phase 7D doc pass.

---

## 10. Technical Debt

Accumulated items that are not blocking but increase carrying cost.

| Debt | Tied gap | Notes |
|------|----------|-------|
| **Dead `http_client` seam** | G5 | Plumbed across 4 modules, used by none. Either wire or remove. |
| **Duplicate config defaults** | G11 | Defaults live in both loader accessors and consumer `.get()` calls. Single-source-of-truth refactor deferred. |
| **Chunk-size key drift** | G9 | Latent silent no-op; must be normalised once the loader is real. |
| **Stale `create_session` docstring** | G7/G13 | Minor prose drift; low cost to fix in the doc pass. |
| **`get_page_count` orphan** | G6 | Unused placeholder; decide delete-vs-defer. |
| **No CI / coverage gate** | G15 | Local-only verification; carrying green-on-my-machine risk. |
| **`tests/` flat layout** | (process) | Only `tests/unit/` exists (empty-ish); no clear unit-vs-integration split despite the naming of several files. Organisational debt; non-blocking. |

> None of the above requires touching the frozen core contracts
> (`BaseAdapter`, `AdapterRegistry`, `StorageManager`, `ManifestManager`,
> data models). All are resolvable at the entry edges or in documentation.

---

## 11. Risks

Risks are the *consequences if gaps are left unresolved or are closed
carelessly*. Each is mapped to the gap(s) that drive it.

### R1 — Silent no-op masquerading as success (Critical risk)

- **Driven by:** G1 + G2 + G7.
- **Description:** The placeholder loader returns valid-looking data and the
  stub entry point prints "Ready" and exits 0. A user following the README
  sees apparent success while nothing ran. This is the most dangerous
  failure mode because it is invisible: there is no error to investigate.
- **Mitigation:** G1's `_validate()` must reject empty/missing `content_root`,
  missing `version`, and structurally unusable configs **before** the
  pipeline starts, so a bad config can never produce a silent success.
  Combined with a real CLI (G2) and an honest README (G7), the no-op trap
  is eliminated.

### R2 — Untested end-to-end path (High risk)

- **Driven by:** G4.
- **Description:** Even after G1/G2/G3 land, without an integration test the
  wiring could be subtly broken (e.g. the loader populates a key the
  orchestrator reads differently) and the suite stays green.
- **Mitigation:** The Phase 7C real-YAML → orchestrator → on-disk-assertions
  test is the single artefact that converts "unit-tested" to
  "system-verified."

### R3 — Documentation drift (High risk)

- **Driven by:** G7.
- **Description:** README describes capabilities the code lacks. Users and
  contributors reason from false premises.
- **Mitigation:** Align docs *only after* the corresponding code ships and
  is verified (Phase 7D). Do not document aspirational behaviour.

### R4 — Key-name drift / silent misconfiguration (Medium risk)

- **Driven by:** G9, G11.
- **Description:** `chunk_size_bytes` (config/docs) vs `chunk_size` (code);
  duplicated defaults across layers. Tuning appears to work but does not.
- **Mitigation:** Loader-side canonicalisation (V10) + single-source-of-truth
  defaults.

### R5 — Data-write during intended dry-run (High risk, data-safety)

- **Driven by:** G8, G3.
- **Description:** `--dry-run` / `dry_run: true` not honoured → files written
  to disk and network hit during what the user believes is a plan-only run.
- **Mitigation:** Two-layer dry-run guard (orchestrator short-circuit +
  descriptor-level safety net) per Technical Design §4.

### R6 — Exception leakage at the CLI boundary (Medium risk, UX)

- **Driven by:** G10.
- **Description:** Without explicit handling, a `ConfigValidationError`
  surfaces as a traceback (exit 1) rather than the documented clean exit 2.
- **Mitigation:** Composition root wraps loader construction in
  `try/except` and maps to exit 2.

### R7 — Frozen-core violation during completion (Process risk)

- **Driven by:** the act of closing G1–G3.
- **Description:** The low-risk framing of Phase 7 depends on the frozen
  core *staying* frozen. A well-intentioned change to `BaseAdapter` or
  `RunSummary` during CLI wiring could cascade.
- **Mitigation:** Phase 7 consumes the core; it does not modify it. Any
  change to a frozen contract must be explicitly justified and is out of
  scope for the completion milestones.

---

## 12. Priority Matrix

Gaps ordered by **severity → criticality of dependency → implementation
cost (cheapest first within a band)**. "Unblocks" lists the gaps that cannot
start until this one is resolved.

| Rank | Gap | Sev | Section | Effort | Unblocks | Phase |
|------|-----|-----|---------|--------|----------|-------|
| 1 | **G1** ConfigLoader placeholder + validation | **Critical** | 2,3,5,7 | S–M | G2, G3, G8, G9, G4 | **7A** |
| 2 | **G2** `main.py` stub / no orchestrator invocation | **Critical** | 2,3,6 | S | G3, G4, G12 | **7B** |
| 3 | **G3** Documented CLI flags absent | **Critical** | 2,6 | M | G14, G7 | **7B** |
| 4 | **G8** Dry-run not propagated | **High** | 2,4 | S | G3 (truthful `--dry-run`) | **7B** |
| 5 | **G4** No real-`ConfigLoader` E2E test | **High** | 8 | M | G7, G15 | **7C** |
| 6 | **G7** README "Production ready" + fictional CLI | **High** | 9 | S | (trust) | **7D** |
| 7 | **G9** `chunk_size` vs `chunk_size_bytes` drift | **Medium** | 5 | S | (after G1) | 7A (in loader) |
| 8 | **G10** Exit-code / exception mapping at boundary | **Medium** | 4 | Trivial | (UX) | 7B (in CLI) |
| 9 | **G5** Dead `http_client` seam | **Medium** | 4 | L–M | (clarity) | Hardening (post-7D) |
| 10 | **G11** Duplicated config defaults | **Medium** | 5 | M | (maintainability) | Hardening (post-7D) |
| 11 | **G12** No `--config` arg / console-script verification | **Medium** | 6 | S | (packaging) | 7B/7C |
| 12 | **G15** No CI / coverage gate | **Low** | 8 | L | (shared-branch safety) | 7C/7D |
| 13 | **G13** Validation contract undocumented | **Low** | 7 | L | (docs) | 7D |
| 14 | **G14** No CLI flag tests | **Low** | 8 | S–M | (regression safety) | 7B/7C |
| 15 | **G6** `get_page_count` orphan `TODO` | **Low** | 3,7 | L | (decision) | Hardening (defer) |

**Reading the matrix:** The top three (G1, G2, G3) are the entry-point
breaks and form the **critical path**. Nothing else can be meaningfully
verified until they exist. G8 and G9 are cheap to fold into the loader/CLI
work and *must* be, because they are silent-failure traps. G4 is the
verification keystone. G7 is the user-facing reconciliation. Everything
below rank 7 is non-blocking hardening and can follow.

---

## Recommended Phase 7 execution order

The phases are sequenced so each is **independently verifiable** and so
that verification at each step is possible (no phase requires artefacts a
later phase produces).

### Phase 7A — ConfigLoader

- **Closes:** G1 (incl. the G9 chunk-size alias V10, and the validation
  rule set V1–V10).
- **Scope:** Implement `_load()` (real YAML read, `FileNotFoundError` /
  `ConfigValidationError`) and `_validate()` (schema version, `general`
  mapping, non-empty `content_root`, numeric types/ranges, per-board
  `REQUIRED_FIELDS`, NCERT template placeholders, chunk-size aliasing).
- **Verify against:** the pre-specified test matrix CL-T1…CL-T11
  (Technical Design §2.3).
- **Why first:** It is the root of the critical path; it touches no frozen
  contract; it is the lowest-risk milestone; and every later phase consumes
  a validated `config` dict.

### Phase 7B — CLI

- **Closes:** G2, G3, G8, G10, G12.
- **Scope:** Rewrite `main()` as a thin composition root with `argparse`
  (`--config`, `--dry-run`, `--board`, `--verify-only`); wire the exit-code
  mapping (0/1/2) with explicit `ConfigValidationError`/`FileNotFoundError`
  handling; implement dry-run propagation (orchestrator short-circuit +
  descriptor-level guard).
- **Verify against:** CLI-T1…CLI-T6 (Technical Design §3.5).
- **Why second:** Depends on a real loader (7A). Once present, the framework
  is runnable end-to-end for the first time.

### Phase 7C — Integration testing

- **Closes:** G4, G14, G15.
- **Scope:** The real-YAML → `ConfigLoader` → `PipelineOrchestrator` →
  on-disk-assertions test; CLI flag tests (dry-run no-write, `--board`
  scoping, `--verify-only` no-download); a minimal CI workflow running
  pytest + the coverage gate.
- **Why third:** Can only meaningfully test a path that exists (7A + 7B).
  This is the milestone that converts the release from "components-verified"
  to "system-verified."

### Phase 7D — Documentation update

- **Closes:** G7, G13 (and the stale-docstring reconciliation folded under
  G5/G11).
- **Scope:** Align README status and CLI examples with shipped, verified
  behaviour; qualify/remove "Production ready" until 7C passes; document the
  composed validation contract; reconcile stale docstrings.
- **Why last:** Documentation must describe code that exists and has been
  verified — never aspirational behaviour. Editing docs before the code
  ships re-creates the exact drift (R3) this phase is meant to eliminate.

---

*End of Phase 7 Gap Analysis. This document is analysis only; it modifies no
production code, tests, the README, or git history.*
