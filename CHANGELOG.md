# Changelog

All notable changes to the EDF-L1 project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7.0] — 2026-07-02

### Added

- **ConfigLoader** (`src/edf/core/config.py`): YAML-based configuration loading with
  schema validation, type coercion, environment variable overrides, and comprehensive
  defaults for all board-specific and pipeline settings.
- **Production CLI** (`main.py`): Full argument parser with `--config`, `--dry-run`,
  `--board`, and `--verify-only` flags. Registered as `edf` entry point in
  `pyproject.toml`.
- **Integration test suite** (`tests/test_phase7c_integration.py`): End-to-end tests
  exercising ConfigLoader → PipelineOrchestrator → board adapters with mocked HTTP
  layer.
- **CLI tests** (`tests/test_cli.py`): Argument parsing, exit-code mapping, and
  orchestration integration tests.
- **ConfigLoader tests** (`tests/test_config_loader.py`): 28 tests covering YAML
  parsing, validation errors, defaults, overrides, and edge cases.

### Changed

- `pyproject.toml` version bumped from `0.1.0` to `0.7.0` to reflect release version.
- README status line, CLI usage examples, and project status table updated for
  Phase 7 scope.
- README Python requirement corrected from `3.12+` to `3.10+` to match
  `pyproject.toml` `requires-python`.

---

## [0.6.0] — Phase 6 (NCERT + Multi-Board)

### Added

- **NCERT adapter** (`src/edf/adapters/ncert.py`): Full NCERT textbook PDF
  descriptor generation and download support.
- **AdapterRegistry** (`src/edf/adapters/registry.py`): Board discovery, enable/disable,
  and multi-board orchestration via `AdapterRegistry.default_registry()`.
- Multi-board aggregation pipeline support in `PipelineOrchestrator`.

---

## [0.5.0] — Phase 5 (Hardening & Verification)

### Added

- Hardening of existing adapters, pipeline, storage, and manifest subsystems.
- Full verification report (`VERIFICATION_REPORT_PHASE5.md`).
- Phase 5 baseline documentation (`PHASE5_BASELINE.md`).

---

## [0.4.0] — Phase 4 (Storage & Manifests)

### Added

- **StorageManager** (`src/edf/storage/manager.py`): Atomic writes, SHA-256 checksum
  registry, deduplication, and path management.
- **ManifestManager** (`src/edf/manifests/manager.py`): Entry registration, merging,
  and `ManifestEntry` model.

---

## [0.3.0] — Phase 3 (Download Pipeline)

### Added

- **DownloadPipeline** (`src/edf/core/downloader.py`): Per-board download orchestration
  with validation.
- **HTTP utilities** (`src/edf/utils/http.py`): Request handling with retry support.
- **PDF utilities** (`src/edf/utils/pdf.py`): PDF validation helpers.

---

## [0.2.0] — Phase 2 (GSEB Adapter)

### Added

- **GSEB adapter** (`src/edf/adapters/gseb.py`): GSEB textbook PDF descriptor generation.
- **BaseAdapter** contract (`src/edf/adapters/base.py`): Abstract interface for all board
  adapters.
- Pre-flight checks and descriptor validation.

---

## [0.1.0] — Phase 1 (Foundation)

### Added

- Project skeleton with package layout under `src/edf/`.
- **Models** (`src/edf/models/data.py`): `DownloadDescriptor`, `RunSummary`, `PreflightIssue`,
  `ManifestEntry`.
- **Logging** (`src/edf/logging/logger.py`): `EDFLogger` with Rich console output.
- **PipelineOrchestrator** (`src/edf/core/pipeline.py`): Board-agnostic orchestration.
- CLI bootstrap in `main.py`.
- MIT license.
