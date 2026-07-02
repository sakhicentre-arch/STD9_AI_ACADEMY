# Release Notes — v0.7.0

**Release date:** 2026-07-02
**Phase:** 7 — Production CLI, ConfigLoader, Integration Tests
**Branch:** `phase7-release`
**Status:** Final validation pending

---

## Summary

Phase 7 delivers the three missing pillars for production-readiness: a validated
configuration loader, a polished CLI entry point, and an end-to-end integration
test suite. Together with the existing Phase 1–6 codebase, EDF-L1 is now a
fully-tested, configurable, CLI-driven PDF acquisition framework.

---

## What Changed

### Phase 7A — ConfigLoader

- **Module:** `src/edf/core/config.py`
- YAML-based configuration loading with `ConfigLoader` class.
- Schema validation via `ConfigValidationError` exception hierarchy.
- Type coercion for all scalar fields (strings, ints, floats, bools).
- Environment variable overrides with `EDF_` prefix (e.g. `EDF_DRY_RUN=true`).
- Comprehensive defaults so `config.yaml` can be minimal.
- 28 dedicated tests in `tests/test_config_loader.py`.

### Phase 7B — Production CLI

- **Module:** `main.py` (refactored from bootstrap to full argument parser)
- `argparse`-based CLI with:
  - `edf` / `edf run` — run the full pipeline.
  - `--config PATH` — custom YAML config path (default: `config.yaml`).
  - `--dry-run` — plan without downloading or mutating manifests.
  - `--board NAME` — restrict to a single board adapter.
  - `--verify-only` — re-validate existing files only.
- Exit-code mapping: 0 = success, 1 = partial failure, 2 = fatal error.
- Registered as `edf` console script in `pyproject.toml`.
- 8 dedicated tests in `tests/test_cli.py`.

### Phase 7C — Integration Test Suite

- **Module:** `tests/test_phase7c_integration.py`
- End-to-end tests exercising ConfigLoader → PipelineOrchestrator → board adapters.
- HTTP layer fully mocked via `requests-mock`.
- Validates configuration-driven pipeline execution, dry-run paths, and error handling.

---

## Defects Fixed During Release Engineering

| ID | Severity | Description | Fix |
|----|----------|-------------|-----|
| D1 | **Release blocker** | `pyproject.toml` declared `version = "0.1.0"` instead of `0.7.0` | Bumped to `0.7.0` |
| D2 | Documentation | README status line referenced Phase 6 and 230 tests | Updated to Phase 7 with correct test count |
| D3 | Documentation | README listed `Python 3.12+` requirement | Corrected to `3.10+` to match `pyproject.toml` |
| D4 | Documentation | CLI examples only showed `python main.py` invocation | Added `edf` entry point examples alongside direct invocation |

---

## Installation

```bash
git clone <repo-url> STD9_AI_ACADEMY
cd STD9_AI_ACADEMY
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp config/config.yaml.example config.yaml
edf --dry-run
```

Or install as a package:

```bash
pip install .
edf --dry-run
```

---

## Test Suite

- **10 test modules**, **309 test functions/classes**.
- Coverage target: **≥ 80%** of `src/edf/`.

```bash
pytest
pytest --cov=src/edf --cov-report=term-missing
```

---

## Configuration

Configuration is loaded from `config.yaml` (or path specified via `--config`).
See `config/config.yaml.example` for the full schema with inline documentation.

Key sections:
- `general.dry_run` — simulate without file changes.
- `general.content_root` — root directory for downloaded PDFs.
- `boards.gseb` / `boards.ncert` — board-specific textbook lists and options.
- `logging.level` — runtime log verbosity.

Environment overrides use the `EDF_` prefix:
```bash
EDF_DRY_RUN=true edf
EDF_BOARD=GSEB edf
```

---

## Files Delivered in This Phase

```
src/edf/core/config.py              — ConfigLoader, ConfigValidationError
main.py                             — Production CLI (refactored)
tests/test_config_loader.py        — 28 ConfigLoader tests
tests/test_cli.py                  — 8 CLI integration tests
tests/test_phase7c_integration.py  — End-to-end integration tests
docs/releases/RELEASE_v0.7.0.md    — This file
CHANGELOG.md                       — Project changelog (new)
```

---

## Upgrading from v0.6.0

1. Pull the `phase7-release` branch.
2. Install updated dependencies: `pip install -r requirements.txt`.
3. Copy the new `config/config.yaml.example` and merge with your existing config.
4. The `edf` entry point is now available after `pip install .` (or use `python main.py`).
5. Run `edf --dry-run` to verify configuration loading.

---

## Checklist

- [x] All Phase 7A/7B/7C code merged to `phase7-release`.
- [x] `pyproject.toml` version is `0.7.0`.
- [x] README status, CLI examples, and Python requirement updated.
- [x] CHANGELOG.md created with complete phase history.
- [x] Release notes document created.
- [x] Full test suite validated (pending final run).
- [ ] Git tag `v0.7.0` applied (awaiting approval).
- [ ] Merge to `main` (awaiting approval).
