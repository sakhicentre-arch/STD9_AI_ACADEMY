"""
EDF-L1 — Education Download Framework, Level 1.

CLI entry point for the EDF-L1 pipeline.

This module is the composition root: it parses command-line arguments, loads
and (optionally) overrides configuration, builds the logger + orchestrator,
runs the pipeline, and maps the result to a process exit code.

Usage::

    edf [run] [--config PATH] [--dry-run] [--board NAME] [--verify-only]

The optional positional ``run`` subcommand is accepted for parity with the
README's ``edf run`` examples but is not required — bare ``edf`` runs the
pipeline too.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

from src.edf.core.config import ConfigLoader, ConfigValidationError
from src.edf.core.pipeline import PipelineOrchestrator
from src.edf.logging.logger import EDFLogger

# ---------------------------------------------------------------------------
# Exit-code mapping (mirrors RunSummary.exit_code semantics in models/data.py)
#   0 — success (all attempted succeeded, or nothing to do / dry-run)
#   1 — partial failure (summary.failed > 0 but < attempted)
#   2 — fatal / configuration error / pre-flight ERROR
# ---------------------------------------------------------------------------
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_FATAL = 2


def build_parser() -> argparse.ArgumentParser:
    """
    Build the EDF-L1 argument parser.

    Returns:
        A configured ``ArgumentParser`` (not yet parsed).
    """
    parser = argparse.ArgumentParser(
        prog="edf",
        description=(
            "EDF-L1: Education Download Framework. "
            "Acquire, validate, and manifest GSEB/NCERT textbook PDFs."
        ),
    )
    # Optional positional subcommand. The README documents ``edf run``; we
    # accept it for ergonomic parity but a bare ``edf`` invocation also runs
    # the pipeline. ``nargs="?"`` keeps it optional.
    parser.add_argument(
        "command",
        nargs="?",
        choices=["run"],
        default="run",
        help="Subcommand to run (default: run). Currently only 'run' is "
        "supported and may be omitted.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to the YAML configuration file (default: config.yaml).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Plan the run (collect descriptors, run pre-flight) but write "
        "no files and mutate no manifest. Overrides config 'general.dry_run'.",
    )
    parser.add_argument(
        "--board",
        type=str,
        default=None,
        metavar="NAME",
        help="Restrict the run to a single board (e.g. GSEB, NCERT). "
        "Case-insensitive. When omitted, every enabled board runs.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        default=False,
        help="Re-validate existing files on disk (header, size, checksum) "
        "without downloading anything.",
    )
    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        argv: Argument vector (defaults to ``sys.argv[1:]``).

    Returns:
        The parsed argument namespace.
    """
    return build_parser().parse_args(argv)


def _apply_cli_overrides(loader: ConfigLoader, args: argparse.Namespace) -> None:
    """
    Apply CLI flags onto the loaded configuration.

    Mutates the loader's in-memory config in place. ``--dry-run`` forces the
    effective ``general.dry_run`` flag to True regardless of the YAML value;
    the orchestrator reads this via ``loader.is_dry_run``.

    Args:
        loader: The validated ConfigLoader whose config to override.
        args:   Parsed CLI arguments.
    """
    if getattr(args, "dry_run", False):
        loader.config.setdefault("general", {})["dry_run"] = True
    # --board and --verify-only are consumed by the orchestrator directly
    # (run(board=..., verify_only=...)), so they need no config mutation here.


def _level_from_config(loader: ConfigLoader) -> int:
    """Map the configured logging level string to a ``logging`` constant."""
    level_name = str(
        loader.logging_config.get("level", ConfigLoader.DEFAULT_LOG_LEVEL)
    ).upper()
    return getattr(logging, level_name, logging.INFO)


def build_orchestrator(
    loader: ConfigLoader, args: argparse.Namespace
) -> PipelineOrchestrator:
    """
    Construct and initialize a PipelineOrchestrator for the run.

    Factored out so tests can exercise wiring without re-parsing argv.

    Args:
        loader: Validated, CLI-overridden ConfigLoader.
        args:   Parsed CLI arguments (unused at present but kept for symmetry
                and future flags that affect construction).

    Returns:
        An initialized, ready-to-run PipelineOrchestrator.
    """
    log_dir = loader.content_root / loader.edf_metadata_dir / "logs"
    logger_instance = EDFLogger(log_dir=log_dir, level=_level_from_config(loader))
    orchestrator = PipelineOrchestrator()
    orchestrator.initialize(loader, logger_instance)
    return orchestrator


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for EDF-L1.

    Parses arguments, loads configuration (applying CLI overrides), runs the
    pipeline, and returns the appropriate exit code.

    Args:
        argv: Optional argument list (for testing). Defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code: 0 (success), 1 (partial failure), 2 (fatal/config).
    """
    args = parse_args(argv)

    # --- Load + validate configuration ---
    try:
        loader = ConfigLoader(args.config)
    except FileNotFoundError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_FATAL
    except ConfigValidationError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return EXIT_FATAL

    # --- Apply CLI overrides (e.g. --dry-run forces dry-run mode) ---
    _apply_cli_overrides(loader, args)

    # --- Build + run the orchestrator ---
    orchestrator = build_orchestrator(loader, args)
    try:
        result = orchestrator.run(
            board=args.board,
            verify_only=args.verify_only,
        )
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        logging.getLogger(__name__).error("Pipeline crashed: %s", exc)
        return EXIT_FATAL
    finally:
        orchestrator.shutdown()

    return int(result.get("exit_code", EXIT_FATAL))


if __name__ == "__main__":
    sys.exit(main())
