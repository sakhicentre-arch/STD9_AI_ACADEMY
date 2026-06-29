#!/usr/bin/env python3
"""
EDF-L1 — Full-suite verification runner.

Executes the complete pytest suite and prints a concise summary:
    - total tests
    - passed
    - failed
    - duration (seconds)
    - exit code

Returns a non-zero exit code on any failure so this script is safe to wire
into CI / pre-merge gates.

Usage:
    python scripts/verify_all.py
    python scripts/verify_all.py --verbose
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Resolve the project root from this file's location regardless of CWD.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full EDF-L1 pytest suite.")
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Pass -v to pytest for per-test output.",
    )
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "pytest", "tests"]
    if args.verbose:
        cmd.append("-v")

    start = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True
    )
    duration = time.perf_counter() - start

    # Echo the run's output so the user sees live detail.
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    passed, failed = _parse_summary(proc.stdout)
    total = passed + failed

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total tests : {total}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")
    print(f"Duration    : {duration:.2f}s")
    print(f"Exit code   : {proc.returncode}")
    print("=" * 60)

    # Non-zero exit code on failure (or on pytest's own non-zero exit).
    return proc.returncode


def _parse_summary(stdout: str) -> tuple[int, int]:
    """Parse pytest's final summary line for passed/failed counts.

    Handles forms like:
        '=== 174 passed in 3.52s ==='
        '=== 170 passed, 4 failed in 3.52s ==='
        '=== 2 failed, 170 passed in 3.52s ==='
    """
    passed = 0
    failed = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("="):
            continue
        low = line.lower()
        if "passed" not in low and "failed" not in low:
            continue
        if "passed" in low:
            passed += _grab_int_before(low, "passed")
        if "failed" in low:
            failed += _grab_int_before(low, "failed")
        # Final summary line found; stop scanning tracebacks etc.
        break
    return passed, failed


def _grab_int_before(text: str, keyword: str) -> int:
    """Return the integer immediately preceding `keyword` in text."""
    idx = text.find(keyword)
    if idx == -1:
        return 0
    # Walk backwards over digits, commas, and spaces to find the number.
    i = idx - 1
    while i >= 0 and (text[i].isdigit() or text[i] in ", "):
        i -= 1
    num_str = text[i + 1:idx].replace(",", "").strip()
    try:
        return int(num_str) if num_str else 1  # 'passed' with no count == 1
    except ValueError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
