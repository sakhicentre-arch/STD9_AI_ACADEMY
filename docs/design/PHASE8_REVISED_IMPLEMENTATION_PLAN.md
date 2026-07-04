# Phase 8 Revised Implementation Plan — EDF-L1 v0.8.0

> **Status:** Draft for Approval
> **Date:** 2026-07-04
> **Baseline:** v0.7.0
> **Target:** v0.8.0

---

## 1. Implementation Principles

All Phase 8 development must satisfy these constraints:

| Principle | Description |
|-----------|-------------|
| **Backward compatible** | Every existing config, CLI invocation, and adapter interface works unchanged |
| **Additive only** | New features are additions, not replacements of existing behavior |
| **Config-gated** | New behaviors (parallel downloads, progress, checkpoint) have sensible defaults and can be disabled |
| **Minimal dependencies** | Target: 0 new runtime dependencies |
| **Preserve architecture** | No paradigm shifts — sequential CLI batch model retained |
| **Preserve interfaces** | `ConfigLoader`, `PipelineOrchestrator`, `AdapterRegistry`, `DownloadPipeline`, `BaseAdapter` — all public APIs unchanged |
| **Test-first for new code** | New modules achieve ≥ 90% coverage; existing modules maintain ≥ 80% |

---

## 2. Phase 8A — Reliability Implementation

### 2.1 Checkpoint Manager (`src/edf/core/checkpoint.py`)

**Design:**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

@dataclass
class CheckpointEntry:
    descriptor_key: str
    status: str  # "completed", "failed", "in_progress"
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class CheckpointManager:
    def __init__(self, storage_manager) -> None:
        """Load existing checkpoint from .edf/checkpoint.json if present."""

    def is_completed(self, descriptor_key: str) -> bool:
        """Check if a descriptor was already successfully downloaded."""

    def mark_completed(self, descriptor_key: str, sha256: str, size_bytes: int) -> None:
        """Record a successful download."""

    def mark_failed(self, descriptor_key: str) -> None:
        """Record a failed download."""

    def mark_in_progress(self, descriptor_key: str) -> None:
        """Mark a descriptor as currently being downloaded."""

    def get_pending(self, all_keys: List[str]) -> List[str]:
        """Return keys not yet completed (filter out completed and in-progress)."""

    def clear(self) -> None:
        """Remove checkpoint file."""

    def expire(self, max_age_hours: int = 168) -> int:
        """Remove entries older than max_age_hours. Returns count removed."""
```

**Key decisions:**

- **Descriptor key:** Use a deterministic key derived from `(board, filename, url)` to avoid collisions across runs.
- **Atomic writes:** Use `StorageManager.atomic_write_bytes()` for checkpoint persistence.
- **Lock:** Use `threading.Lock` for thread safety (needed by 8B parallel downloads).
- **Expiry:** Auto-expire on load; entries older than `max_age_hours` (default 168 = 7 days) are removed.

### 2.2 Resume Logic

**Integration in `DownloadPipeline`:**

```python
class DownloadPipeline:
    def __init__(self, storage_manager, manifest_manager, config):
        self._checkpoint = None  # Lazy init
        self._checkpoint_lock = threading.Lock()

    def _init_checkpoint(self):
        if self._config.get("checkpoint", {}).get("enabled", True):
            self._checkpoint = CheckpointManager(self._storage_manager)
            max_age = self._config.get("checkpoint", {}).get("max_age_hours", 168)
            expired = self._checkpoint.expire(max_age)

    def run(self, descriptors, run_id="", force=False):
        self._init_checkpoint()
        if self._checkpoint and not force:
            all_keys = [self._descriptor_key(d) for d in descriptors]
            pending_keys = set(self._checkpoint.get_pending(all_keys))
            descriptors = [d for d in descriptors
                          if self._descriptor_key(d) in pending_keys]
        # ... existing download logic

    def _process_descriptor(self, descriptor):
        if self._checkpoint:
            key = self._descriptor_key(descriptor)
            with self._checkpoint_lock:
                self._checkpoint.mark_in_progress(key)
        # ... download, validate, store ...
        if success:
            with self._checkpoint_lock:
                self._checkpoint.mark_completed(key, sha256, size)
        else:
            with self._checkpoint_lock:
                self._checkpoint.mark_failed(key)
```

**Key decisions:**

- `--resume` loads checkpoint and filters out completed descriptors before starting.
- `--force` overrides resume (re-downloads everything).
- Without `--resume`, checkpoint is still written (for future resume) but not loaded at startup.
- Checkpoint is cleared on fully successful run (all descriptors succeeded).

### 2.3 Graceful Shutdown

**Integration in `PipelineOrchestrator`:**

```python
class PipelineOrchestrator:
    def run(self, board=None, verify_only=False):
        self._shutdown_requested = False
        original_handler = signal.signal(signal.SIGINT, self._handle_shutdown)

        try:
            # ... existing pipeline phases ...
        finally:
            signal.signal(signal.SIGINT, original_handler)
            if self._shutdown_requested:
                self.logger.info("Shutdown requested. Saving checkpoint...")
                # Checkpoint is already saved per-descriptor

    def _handle_shutdown(self, signum, frame):
        self._shutdown_requested = True
        self.logger.warning("Interrupt received. Finishing current download...")
```

**Key decisions:**

- SIGINT handler sets a flag; does NOT raise an exception.
- The download loop checks `_shutdown_requested` between descriptors and breaks cleanly.
- The current descriptor is allowed to complete (no partial writes).
- Result dict includes `"interrupted": true` when shutdown was requested.
- Exit code 1 (partial failure) on interrupt.

### 2.4 Config Validation Extensions

**New defaults in `ConfigLoader`:**

```python
DEFAULTS["download"]["parallel_max"] = 1
DEFAULTS["download"]["per_board_delay"] = 1.0
DEFAULTS["checkpoint"]["enabled"] = True
DEFAULTS["checkpoint"]["max_age_hours"] = 168
DEFAULTS["progress"]["enabled"] = True
DEFAULTS["progress"]["format"] = "text"
```

**New validation rules:**

| Rule | Field | Condition | Error |
|------|-------|-----------|-------|
| V11 | `download.parallel_max` | present and not positive integer | `ConfigValidationError` |
| V12 | `download.per_board_delay` | present and not non-negative number | `ConfigValidationError` |
| V13 | `boards.<name>.rate_limit_rpm` | present and not positive integer or null | `ConfigValidationError` |
| V14 | `checkpoint.max_age_hours` | present and not non-negative integer | `ConfigValidationError` |

---

## 3. Phase 8B — Performance Implementation

### 3.1 Progress Tracker (`src/edf/core/progress.py`)

**Design:**

```python
from dataclasses import dataclass
from typing import Optional, Callable
import time

@dataclass
class ProgressReport:
    filename: str
    bytes_downloaded: int
    total_bytes: Optional[int]
    elapsed_seconds: float
    speed_bytes_per_sec: float
    percent: Optional[float]  # None if total_bytes unknown

class ProgressTracker:
    def __init__(self, filename: str, total_bytes: Optional[int] = None):
        self._filename = filename
        self._total_bytes = total_bytes
        self._bytes_downloaded = 0
        self._start_time = time.monotonic()
        self._last_report_time = 0.0
        self._callback: Optional[Callable[[ProgressReport], None]] = None

    def set_callback(self, callback: Callable[[ProgressReport], None]) -> None:
        self._callback = callback

    def update(self, bytes_chunk: int) -> None:
        self._bytes_downloaded += bytes_chunk
        now = time.monotonic()
        # Throttle reports to at most once per 0.5 seconds
        if now - self._last_report_time >= 0.5:
            self._report()

    def finish(self) -> ProgressReport:
        return self._report(force=True)

    def _report(self, force=False) -> ProgressReport:
        elapsed = time.monotonic() - self._start_time
        speed = self._bytes_downloaded / elapsed if elapsed > 0 else 0
        percent = (self._bytes_downloaded / self._total_bytes * 100) if self._total_bytes else None
        report = ProgressReport(
            filename=self._filename,
            bytes_downloaded=self._bytes_downloaded,
            total_bytes=self._total_bytes,
            elapsed_seconds=elapsed,
            speed_bytes_per_sec=speed,
            percent=percent,
        )
        if self._callback:
            self._callback(report)
        return report
```

**Integration in `utils/http.py download_stream()`:**

```python
def download_stream(url, dest, chunk_size=8192, timeout=120,
                    max_retries=3, progress_callback=None):
    tracker = ProgressTracker(filename=dest.name)
    if progress_callback:
        tracker.set_callback(progress_callback)

    response = session.get(url, stream=True, timeout=timeout)
    total_bytes = int(response.headers.get("Content-Length", 0)) or None
    tracker = ProgressTracker(filename=dest.name, total_bytes=total_bytes)

    for chunk in response.iter_content(chunk_size=chunk_size):
        dest.write(chunk)
        tracker.update(len(chunk))
```

### 3.2 Parallel Downloads

**Design in `DownloadPipeline.run()`:**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

class DownloadPipeline:
    def run(self, descriptors, run_id="", force=False):
        parallel_max = self._config.get("download", {}).get("parallel_max", 1)

        if parallel_max <= 1 or len(descriptors) <= 1:
            # Sequential path (v0.7.0 behavior)
            return self._run_sequential(descriptors, run_id, force)
        else:
            return self._run_parallel(descriptors, run_id, force, parallel_max)

    def _run_parallel(self, descriptors, run_id, force, max_workers):
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._process_descriptor, d): d
                for d in descriptors
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        return self._aggregate_results(results)
```

**Key decisions:**

- `parallel_max` defaults to 1 — no behavior change unless explicitly configured.
- Each thread gets its own `requests.Session` (thread-safe by default).
- Checkpoint writes are protected by `threading.Lock`.
- Progress callbacks use the logger (already serialized via `logging` module).
- Rate limiting is enforced at the thread pool submission level, not per-thread.

### 3.3 Per-Board Rate Limiting

**Design:**

```python
import time

class RateLimiter:
    def __init__(self, requests_per_minute: Optional[int] = None,
                 min_delay: float = 0.0):
        self._rpm = requests_per_minute
        self._min_delay = min_delay
        self._last_request_time: Dict[str, float] = {}

    def wait(self, board: str) -> None:
        """Block until the rate limit allows the next request for this board."""
        if self._rpm:
            min_interval = 60.0 / self._rpm
            last = self._last_request_time.get(board, 0)
            elapsed = time.monotonic() - last
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        self._last_request_time[board] = time.monotonic()
```

**Integration:** `DownloadPipeline._process_descriptor()` calls `rate_limiter.wait(descriptor.board)` before each download.

---

## 4. Phase 8C — Packaging Implementation

### 4.1 PyPI Packaging

**`pyproject.toml` updates:**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "edf-l1"
version = "0.8.0"
description = "Batch PDF download framework for educational textbooks"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "Amisha Patel"},
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Education",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Utilities",
]

[project.scripts]
edf = "main:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*", "main.py"]
```

**Key decisions:**

- Keep `main.py` at root (as-is) — setuptools can include it via explicit configuration.
- Use `src/` layout for library code; `main.py` is the CLI entry point.
- Test with `pip install .` in a clean venv before any PyPI upload.

### 4.2 Dockerfile

```dockerfile
# Builder stage
FROM python:3.10-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.10-slim
WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY main.py .
COPY src/ src/
COPY config/config.yaml.example config/config.yaml.example

# Create content directory
RUN mkdir -p /app/CONTENT

ENTRYPOINT ["python", "main.py"]
CMD ["run", "--config", "config/config.yaml"]
```

**Key decisions:**

- Multi-stage build for smaller image.
- Base on `python:3.10-slim` (not `alpine` — avoids musl compatibility issues).
- Config is COPY'd as example; users mount real config via volume.
- No `pip install` at runtime — dependencies are pre-installed.

### 4.3 CI Improvements

**GitHub Actions workflow:**

```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov pytest-mock requests-mock
      - run: python -m pytest tests --cov=src/edf --cov-fail-under=85 -v
```

---

## 5. Phase 8D — Developer Experience Implementation

### 5.1 Manifest Diff (`src/edf/manifests/diff.py`)

**Design:**

```python
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

@dataclass
class ManifestDiff:
    added: List[Dict]
    removed: List[Dict]
    changed: List[Tuple[Dict, Dict]]  # (old, new)
    unchanged_count: int
    timestamp_from: Optional[str] = None
    timestamp_to: Optional[str] = None

    def summary(self) -> str:
        return (f"Added: {len(self.added)}, Removed: {len(self.removed)}, "
                f"Changed: {len(self.changed)}, Unchanged: {self.unchanged_count}")

def diff_manifests(
    entries_from: Dict[str, dict],
    entries_to: Dict[str, dict],
    timestamp_from: Optional[str] = None,
    timestamp_to: Optional[str] = None,
) -> ManifestDiff:
    from_keys = set(entries_from.keys())
    to_keys = set(entries_to.keys())

    added = [entries_to[k] for k in (to_keys - from_keys)]
    removed = [entries_from[k] for k in (from_keys - to_keys)]

    changed = []
    unchanged = 0
    for k in from_keys & to_keys:
        if entries_from[k] != entries_to[k]:
            changed.append((entries_from[k], entries_to[k]))
        else:
            unchanged += 1

    return ManifestDiff(
        added=added,
        removed=removed,
        changed=changed,
        unchanged_count=unchanged,
        timestamp_from=timestamp_from,
        timestamp_to=timestamp_to,
    )
```

**Key decisions:**

- Compare entries by path key (same as ManifestManager's key scheme).
- "Changed" means any field differs (sha256, size_bytes, modified_at, etc.).
- Function accepts raw dicts for flexibility; no need to instantiate ManifestEntry.

### 5.2 CLI Subcommands

**Subcommand parser design:**

```python
def build_parser():
    parser = argparse.ArgumentParser(prog="edf", description="EDF-L1 Download Framework")

    subparsers = parser.add_subparsers(dest="command")

    # "run" subcommand (default, backward compatible)
    run_parser = subparsers.add_parser("run", help="Download textbooks")
    run_parser.add_argument("--config", default="config.yaml")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--board", default=None)
    run_parser.add_argument("--verify-only", action="store_true")
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument("--parallel", type=int, default=None)
    run_parser.add_argument("--progress", action="store_true", default=True)

    # "validate-config" subcommand
    vc_parser = subparsers.add_parser("validate-config", help="Validate configuration file")
    vc_parser.add_argument("config", default="config.yaml", nargs="?")

    # "diff" subcommand
    diff_parser = subparsers.add_parser("diff", help="Compare manifest snapshots")
    diff_parser.add_argument("--before", required=True)
    diff_parser.add_argument("--after", required=True)
    diff_parser.add_argument("--json", action="store_true")

    return parser
```

**Backward compatibility:**

- When no subcommand is given, the parser defaults to `"run"` (exact v0.7.0 behavior).
- Positional arguments are still accepted when no subcommand is specified.

### 5.3 JSON Output Mode

**Design:**

When `--json` is passed, the result dict from `PipelineOrchestrator.run()` is serialized to stdout as JSON:

```json
{
  "exit_code": 0,
  "run_id": "edf_2026-07-04_120000",
  "summary": {
    "attempted": 25,
    "succeeded": 24,
    "skipped": 1,
    "failed": 0
  },
  "board_summaries": {
    "GSEB": {"attempted": 10, "succeeded": 10, "skipped": 0, "failed": 0},
    "NCERT": {"attempted": 15, "succeeded": 14, "skipped": 1, "failed": 0}
  },
  "interrupted": false,
  "duration_seconds": 142.5
}
```

**Key decisions:**

- JSON goes to stdout; logging remains on stderr/file.
- Schema is stable (documented in docstring); not versioned for now.
- `--json` can be combined with `--dry-run` and `--verify-only`.

---

## 6. Dependency Map

```
Phase 8A (Reliability)
  ├── CheckpointManager (new module, no deps)
  ├── Graceful Shutdown (depends on CheckpointManager)
  ├── Resume Logic (depends on CheckpointManager)
  └── Config Validation V11-V14 (no deps)

Phase 8B (Performance)
  ├── ProgressTracker (new module, no deps)
  ├── Progress in download_stream (depends on ProgressTracker)
  ├── Parallel Downloads (depends on CheckpointManager from 8A)
  └── Rate Limiting (new class, no deps)

Phase 8C (Packaging)
  ├── PyPI (depends on all source being finalized)
  ├── Dockerfile (depends on PyPI packaging)
  └── CI (depends on Dockerfile, all tests)

Phase 8D (Developer Experience)
  ├── ManifestDiff (new module, no deps)
  ├── CLI Subcommands (depends on ManifestDiff, ConfigLoader)
  ├── JSON Output (depends on PipelineOrchestrator result)
  └── Documentation (depends on all above)
```

---

## 7. Estimated Test Growth

| Milestone | New Tests | New Lines of Test Code (est.) | Cumulative Tests |
|-----------|----------|------------------------------|------------------|
| 8A Reliability | ~36 | ~450 | ~345 |
| 8B Performance | ~31 | ~400 | ~376 |
| 8C Packaging | 0 | 0 | ~376 |
| 8D Dev Experience | ~27 | ~350 | ~403 |
| **Total** | **~94** | **~1,200** | **~403** |

### Coverage Growth

| Module | Current Coverage | Target Coverage |
|--------|-----------------|-----------------|
| `src/edf/core/checkpoint.py` | N/A (new) | ≥ 90% |
| `src/edf/core/progress.py` | N/A (new) | ≥ 90% |
| `src/edf/manifests/diff.py` | N/A (new) | ≥ 90% |
| `src/edf/core/config.py` | ≥ 80% | ≥ 85% (new validation rules) |
| `src/edf/core/downloader.py` | ≥ 80% | ≥ 80% (maintain) |
| `src/edf/core/pipeline.py` | ≥ 80% | ≥ 80% (maintain) |
| **Overall** | ≥ 80% | **≥ 85%** |

---

## 8. Implementation Checklist

### Phase 8A

- [ ] Create `src/edf/core/checkpoint.py`
- [ ] Integrate checkpoint writes in `DownloadPipeline._process_descriptor()`
- [ ] Add `--resume` flag to CLI
- [ ] Add SIGINT handler in `PipelineOrchestrator.run()`
- [ ] Add V11-V14 validation rules in `ConfigLoader`
- [ ] Add checkpoint config defaults
- [ ] Write `test_checkpoint.py` (~15 tests)
- [ ] Write tests for resume logic (~8 tests)
- [ ] Write tests for graceful shutdown (~5 tests)
- [ ] Write tests for V11-V14 (~8 tests)
- [ ] Update `config/config.yaml.example`

### Phase 8B

- [ ] Create `src/edf/core/progress.py`
- [ ] Add progress callback to `utils/http.py download_stream()`
- [ ] Wire progress display in `DownloadPipeline`
- [ ] Add parallel download path in `DownloadPipeline.run()`
- [ ] Implement `RateLimiter` class
- [ ] Add `--parallel N` and `--progress` CLI flags
- [ ] Add `per_board_delay` and `rate_limit_rpm` config defaults
- [ ] Write `test_progress.py` (~10 tests)
- [ ] Write `test_parallel_downloads.py` (~10 tests)
- [ ] Write `test_rate_limiting.py` (~6 tests)
- [ ] Update `config/config.yaml.example`

### Phase 8C

- [ ] Finalize `pyproject.toml` build metadata
- [ ] Test `pip install .` in clean venv
- [ ] Test `python -m build` produces valid wheel + sdist
- [ ] Create `Dockerfile`
- [ ] Create `.dockerignore`
- [ ] Test Docker build and run
- [ ] Create or update GitHub Actions workflow
- [ ] Add coverage gate (≥85%)
- [ ] Update `.gitignore`

### Phase 8D

- [ ] Create `src/edf/manifests/diff.py`
- [ ] Refactor `main.py` to support subcommands
- [ ] Add `edf validate-config` subcommand
- [ ] Add `edf diff` subcommand
- [ ] Add `--json` flag to `edf run`
- [ ] Write `test_manifest_diff.py` (~12 tests)
- [ ] Write CLI extension tests (~12 tests)
- [ ] Write JSON output tests (~6 tests)
- [ ] Update documentation

---

## 9. Comparison with Rejected Implementation Plan

| Dimension | Rejected Plan | Revised Plan |
|-----------|--------------|--------------|
| **Total implementation items** | 41 | ~20 |
| **New Python modules** | ~10+ (SecretProvider, MetricsLayer, PluginRegistry, etc.) | 3 |
| **Total new code** | ~2,000+ lines | ~200 lines |
| **New test code** | Unknown (enterprise test matrix) | ~1,200 lines |
| **Infrastructure needed** | Kubernetes cluster, Prometheus, Grafana, Vault | PyPI account, Docker (optional) |
| **CI complexity** | SAST, SCA, container scanning, multi-stage | pytest + coverage gate |
| **Implementation risk** | High (many new technologies, async refactor) | Low (evolutionary, proven patterns) |

---

*End of PHASE8_REVISED_IMPLEMENTATION_PLAN.md*
