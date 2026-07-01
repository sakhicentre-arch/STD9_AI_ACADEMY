# Phase 7 — Technical Design

> **Purpose:** Translate the Phase 7 architecture into concrete, buildable
> specifications for the two highest-priority deliverables — **ConfigLoader**
> and the **CLI** — plus the supporting dry-run propagation and end-to-end
> verification. Every interface, default, and validation rule cited below is
> derived from the existing Phase 6 source so that Phase 7 *completes* the
> wiring rather than redesigning the core.
>
> **Constraints honoured:** This is a design document only. It proposes no
> changes to production code, tests, the README, or git history.

---

## 1. Design Goals

| ID | Goal | Mapping to gap |
|----|------|----------------|
| DG1 | `ConfigLoader` reads a real YAML file and exposes a validated `dict`. | G1 |
| DG2 | `ConfigLoader` fails fast with actionable errors on misconfiguration. | G1, R1 |
| DG3 | A CLI invokes the orchestrator end-to-end with documented flags. | G2, G3 |
| DG4 | `--dry-run` short-circuits downloads without breaking the manifest summary. | G8 |
| DG5 | A real end-to-end integration test exercises `config.yaml → result`. | G4 |
| DG6 | No public API of the frozen core is changed. | (safety) |

---

## 2. ConfigLoader — Detailed Design

### 2.1 Current State (verbatim evidence)

`src/edf/core/config.py` currently:

- `__init__` calls `self._load()` then `self._validate()`.
- `_load()` (lines 130–143): the real YAML read is **commented out**; the
  body is `self._raw = {"version": "1.0"}  # Placeholder for Phase 1 bootstrap`.
- `_validate()` (lines 145–160): body is `pass`, with a `TODO` listing the
  intended checks.
- Public accessors (`config`, `general`, `download`, `validation`, `ncert`,
  `gseb`, `logging_config`, `content_root`, `edf_metadata_dir`,
  `is_dry_run`, `is_force_overwrite`, `get_textbooks`) are **already
  implemented and stable**. Phase 7 must not change their signatures.

### 2.2 Target Behaviour

#### 2.2.1 `_load()` — file reading

Replace the placeholder with the commented-out intended logic, hardened:

```
def _load(self) -> None:
    if not self._config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {self._config_path}"
        )
    try:
        with open(self._config_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigValidationError(
            f"Malformed YAML in {self._config_path}: {exc}"
        ) from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ConfigValidationError(
            f"Config root must be a mapping, got {type(loaded).__name__}"
        )
    self._raw = loaded
```

**Design notes:**

- `yaml.safe_load` is already the dependency in use (`PyYAML>=6.0,<7.0`).
  No new dependency.
- An empty file yields `{}`, which `_validate()` then rejects (missing
  required keys) — fail-fast, not silent.
- `FileNotFoundError` is preserved as the documented exception for a missing
  path (matches the existing docstring contract).

#### 2.2.2 `_validate()` — validation rules

Validation must enforce the contract the core already assumes. Rules are
derived directly from consumers cited in the Architecture doc §3.3.

| Rule | Check | Failure action |
|------|-------|----------------|
| V1 | `version` present and == `"1.0"` | `ConfigValidationError` |
| V2 | `general` is a mapping | `ConfigValidationError` |
| V3 | `general.content_root` is a non-empty string | `ConfigValidationError` |
| V4 | `download` (if present) is a mapping; numeric fields are ints ≥ 0 | `ConfigValidationError` |
| V5 | `validation` (if present) is a mapping; `min_size_bytes` int ≥ 0 | `ConfigValidationError` |
| V6 | At least one board produces ≥1 textbook OR `boards` explicitly enables a registered board | `ConfigValidationError` (with WARNING context) |
| V7 | Each `gseb.textbooks[]` entry has `std, subject, medium, language, url, filename` | `ConfigValidationError` (per-entry index in message) |
| V8 | Each `ncert.textbooks[]` entry has `code, std, subject, medium, language` | `ConfigValidationError` (per-entry index in message) |
| V9 | `ncert.url_template` / `filename_template` (if present) contain only known placeholders `{code,std,subject,medium,language}` | `ConfigValidationError` |
| V10 | Canonicalize the chunk-size key: accept `chunk_size` **or** `chunk_size_bytes`; store both alias forms so the downloader reads consistently | normalize, no error (resolves G9/R4) |

**Design notes:**

- V6 mirrors the orchestrator's "no descriptors" branch (`pipeline.py:219`)
  but moves the decision to load time so the user is told *before* any work.
  Strictly, an empty-textbook config is currently only a `WARNING`
  (`GSEB_NO_TEXTBOOKS` / `NCERT_NO_TEXTBOOKS`); the loader should treat
  *zero textbooks across all enabled boards* as a **WARNING emitted via
  logging**, not a hard error, to preserve Phase 5/6 semantics. V6 is
  therefore refined to: **error only if config is structurally unusable**
  (e.g., no `general` section at all).
- V7/V8 field sets are copied verbatim from `gseb.py:109` and
  `ncert.py:54` (`REQUIRED_FIELDS`).
- All error messages must include the offending key path, e.g.
  `gseb.textbooks[2]: missing 'url'`.

#### 2.2.3 Backward-compatibility guarantees

- The `boards` section is optional; absence ⇒ all registered boards enabled
  (matches `registry.py:228`). The loader must **not** require it.
- Per-board `enabled` flags inside `gseb`/`ncert` sub-dicts (present in
  `config.yaml.example`) are informational; the authoritative enable/disable
  source is the `boards` section (matches `registry.enabled_boards`).
- Unknown top-level keys are **ignored** (forward compatibility), not errors.

### 2.3 ConfigLoader Test Matrix (design-level)

These are test *specifications*, not the test files (Milestone 2 constraint:
do not write tests yet).

| Test | Input | Expected |
|------|-------|----------|
| CL-T1 | valid full `config.yaml.example` content | loads; `version == "1.0"`; `content_root` resolves |
| CL-T2 | missing file | `FileNotFoundError` |
| CL-T3 | malformed YAML | `ConfigValidationError("Malformed YAML...")` |
| CL-T4 | empty file | `ConfigValidationError` (missing `general`) |
| CL-T5 | root is a YAML list | `ConfigValidationError("must be a mapping")` |
| CL-T6 | `gseb.textbooks[0]` missing `url` | `ConfigValidationError` names index + field |
| CL-T7 | `ncert.textbooks[0]` missing `code` | `ConfigValidationError` names index + field |
| CL-T8 | `download.timeout_seconds: "abc"` | `ConfigValidationError` (type) |
| CL-T9 | no `boards` section, both boards have textbooks | loads; both considered enabled |
| CL-T10 | `chunk_size_bytes` only present | loads; downloader reads `chunk_size` via alias |
| CL-T11 | `version: "2.0"` | `ConfigValidationError` (unsupported version) |

---

## 3. CLI — Detailed Design

### 3.1 Current State

`main.py` `main()` prints `"EDF-L1 Bootstrap Ready"` and returns `0`. It does
not parse arguments and does not call `PipelineOrchestrator`. The README
documents four invocations (`run`, `--dry-run`, `--board`, `--verify-only`)
that do not exist.

### 3.2 Placement Decision

Two viable locations for the CLI. Both are acceptable; the choice is a
Milestone 2 decision point.

| Option | Pros | Cons |
|--------|------|------|
| **A: rewrite `main.py`** (Recommended) | Matches README's `python main.py` examples and `pyproject.toml`'s `[project.scripts] edf = "main:main"`. Zero new files. | `main.py` becomes non-trivial. |
| B: new `src/edf/cli.py` | Separation of parsing from bootstrap. | Requires updating `[project.scripts]`; `python main.py` examples in README would need an import shim. |

**Recommendation:** Option A, keeping `main()` as the argparse entry and
extracting a `build_orchestrator(args)` helper for testability. This honours
the existing `edf = "main:main"` console-script binding.

### 3.3 Argument Specification

```
edf [run] [--config PATH] [--dry-run] [--board NAME] [--verify-only]
```

| Flag | Type | Default | Behaviour |
|------|------|---------|-----------|
| `--config` | path | `config.yaml` | Passed to `ConfigLoader`. Missing file ⇒ `FileNotFoundError`, exit code 2. |
| `--dry-run` | flag | off | Sets effective `general.dry_run = True` regardless of YAML. |
| `--board` | str | none | Restricts the run to one board. Implemented by injecting a synthetic `boards` section `{<board>: {enabled: true}, others: {enabled: false}}` before passing config to the orchestrator, reusing the existing `registry.enabled_boards` machinery. |
| `--verify-only` | flag | off | Re-validates existing files without downloading. Implemented by skipping the download phase descriptors (Phase-3+ path) and running only inventory + pre-flight + manifest re-check. |

**Exit-code mapping** (must match `RunSummary.exit_code` semantics in
`models/data.py:178`):

- `0` — success (all attempted succeeded, or nothing to do).
- `1` — partial failure (`summary.failed > 0` but `< attempted`).
- `2` — fatal / configuration error / pre-flight ERROR.

### 3.4 Composition Root (pseudocode)

```
def main(argv=None) -> int:
    args = parse_args(argv)                      # argparse
    try:
        loader = ConfigLoader(args.config)
    except (FileNotFoundError, ConfigValidationError) as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    effective = _apply_cli_overrides(loader.config, args)  # --dry-run, --board
    logger = EDFLogger(log_dir=Path(loader.content_root) / loader.edf_metadata_dir / "logs",
                       level=_level_from_config(loader))
    orch = PipelineOrchestrator()
    orch.initialize(_as_config_loader_view(effective, loader), logger)
    try:
        result = orch.run() if not args.verify_only else orch.run_verify_only()
    finally:
        orch.shutdown()
    return int(result["exit_code"])
```

**Design notes:**

- `_apply_cli_overrides` returns a new `dict` (never mutates the loader's
  internal state) so repeated runs in one process stay deterministic.
- Because `PipelineOrchestrator.initialize` expects a `ConfigLoader`-shaped
  object (it reads `.config`, `.content_root`, `.edf_metadata_dir`,
  `.is_force_overwrite`), the cleanest path is to add a small
  `_as_config_loader_view()` that wraps the overridden dict. **Alternative
  (preferred if allowed in Milestone 2):** extend `ConfigLoader` with an
  optional `overrides` constructor parameter so the orchestrator continues
  to receive a real `ConfigLoader`. Either preserves the frozen core.
- `--verify-only` requires a new `run_verify_only()` orchestrator path OR a
  `verify_only` flag threaded into `run()`. Since `PipelineOrchestrator` is
  not strictly frozen (it is internal, not a published adapter contract),
  adding a parameter is acceptable; rewriting its internals is not.

### 3.5 CLI Test Matrix (design-level)

| Test | Invocation | Expected |
|------|-----------|----------|
| CLI-T1 | `main(["--config", valid])` | exit 0 (with descriptors) or 0 (none) |
| CLI-T2 | `main(["--config", missing])` | exit 2, stderr names the file |
| CLI-T3 | `main(["--dry-run", "--config", valid])` | exit 0; no files written under CONTENT |
| CLI-T4 | `main(["--board", "GSEB", ...])` | only GSEB adapter instantiated |
| CLI-T5 | malformed config | exit 2, message cites the bad key |
| CLI-T6 | `--verify-only` on empty CONTENT | exit 0; manifest saved |

---

## 4. Dry-Run Propagation (G8)

### 4.1 Current Gap

`ConfigLoader.is_dry_run` exists (`config.py:108`), and `general.dry_run`
is read from YAML, but **nothing in `PipelineOrchestrator.run()` or
`DownloadPipeline` consults it**. A `dry_run: true` config today still
downloads files.

### 4.2 Design

Two-phase check, both gated on the same flag for clarity:

1. **Orchestrator level:** if `config_loader.is_dry_run`, log each intended
   action during pre-flight/collect and **skip** the
   `download_pipeline.run(...)` call, writing only a dry-run summary.
2. **Descriptor level (defence in depth):** `DownloadPipeline._process_descriptor`
   checks a `dry_run` flag and, when set, logs `"DRY-RUN: would download X"`
   and returns `{"status": "skipped", "details": {"reason": "dry_run"}}`
   without touching the network or filesystem.

**Why two layers:** the orchestrator short-circuit gives a clean summary
(no attempted/succeeded/failed distortion); the descriptor-level guard is a
safety net against future code paths that bypass the orchestrator.

### 4.3 Summary semantics under dry-run

Under dry-run, every descriptor counts as `skipped`, so `RunSummary.exit_code`
evaluates to `0` (no failures). This matches user expectations: dry-run is a
"plan, don't act" mode.

---

## 5. End-to-End Verification Strategy (G4)

### 5.1 Gap

No test loads a YAML file through `ConfigLoader` into `PipelineOrchestrator`.
The closest test (`test_multiboard_integration.py`) substitutes a
`SimpleNamespace` for the loader and stubs `DownloadPipeline.run`.

### 5.2 Design

Add (in a later milestone — design only here) a test that:

1. Writes a temp `config.yaml` from `config.yaml.example` with `content_root`
   pointed at a `tmp_path`.
2. Serves a small valid PDF via the existing local-HTTP-server fixture
   pattern from `test_integration_staged.py:47-70`.
3. Constructs `ConfigLoader(tmp_yaml)` for real.
4. Runs `PipelineOrchestrator.run()`.
5. Asserts: exit code 0, one file under `CONTENT/GSEB/`, one manifest entry,
   one checksum registered, `RunSummary.succeeded == 1`.

This is the **single test that converts the framework from
"components-verified" to "system-verified"**.

---

## 6. Implementation Roadmap

Milestones are sized so each is independently verifiable and shippable.
Estimates assume the constraints (no core redesign) hold.

| Milestone | Scope | Deliverables | Est. effort | Depends on |
|-----------|-------|--------------|-------------|------------|
| **M1** (this doc set) | Analysis & design | 3 design docs | — | — |
| **M2** | ConfigLoader | Implement `_load()` + `_validate()`; CL-T1…CL-T11 tests | Small–Medium | M1 approval |
| **M3** | CLI skeleton | `main()` argparse + `--config`; CLI-T1, T2, T5 | Small | M2 |
| **M4** | CLI flags | `--dry-run`, `--board`, `--verify-only`; CLI-T3, T4, T6 | Medium | M3 |
| **M5** | Dry-run propagation | orchestrator + descriptor-level guards (§4) | Small | M2, M4 |
| **M6** | End-to-end test | §5 real-YAML integration test | Medium | M2–M5 |
| **M7** | Hardening & docs | resolve G6 (`get_page_count`) decision, G7 README alignment, G5 `http_client` decision | Small | M6 |

> **M2 is the critical path.** M3–M6 cannot start until a real loader exists.
> M2 is also the lowest-risk milestone (no core changes), making it the ideal
> first implementation step.

---

## 7. Open Questions for Milestone 2

These require a decision before/during ConfigLoader implementation and are
flagged here so they are not discovered mid-build:

1. **CLI placement** (§3.2): rewrite `main.py` (recommended) vs. new
   `src/edf/cli.py`?
2. **Empty-textbook policy** (§2.2.2 V6): warn-and-continue (preserves
   current adapter behaviour) vs. hard error at load time?
3. **`--verify-only` shape** (§3.4): new `run_verify_only()` method vs.
   `verify_only` parameter on `run()`?
4. **Chunk-size aliasing** (§2.2.2 V10): normalize at load time (recommended)
   vs. fix the downloader to read `chunk_size_bytes`?

Each is low-stakes but each changes the shape of Milestone 2/3 code; resolving
them up front avoids rework.

---

## 8. Non-Goals (Phase 7, as scoped here)

- Adding new boards (e.g., CBSE) — registry already supports this; out of
  scope for the wiring-focused Phase 7.
- Replacing `requests` or adding async I/O.
- Implementing `get_page_count()` fully (requires a PDF library decision —
  deferred, see Gap Analysis G6).
- Changing the manifest/checksum on-disk format.
- Modifying the README (constraint; flagged for a later docs milestone).
