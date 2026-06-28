"""
EDF-L1 Logger.

Provides structured dual-output logging:
- Console handler (human-readable, colored)
- File handler (human-readable .log)
- JSONL handler (machine-readable .jsonl)

All log entries include run_id, timestamp, module, and level.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON lines.

    Each line is a valid JSON object with fields:
    ts, run_id, level, module, event, message.
    """

    def __init__(self, run_id: str = "") -> None:
        super().__init__()
        self._run_id = run_id

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        import json

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self._run_id,
            "level": record.levelname,
            "module": record.module,
            "event": record.getMessage(),
        }
        # Include optional details if present
        if hasattr(record, "details") and record.details:
            entry["details"] = record.details
        return json.dumps(entry, ensure_ascii=False)


class EDFLogger:
    """
    Structured logger for EDF-L1 pipeline runs.

    Provides dual-output logging:
        - Console: human-readable with timestamps
        - File (.log): human-readable with timestamps
        - File (.jsonl): machine-readable JSON lines

    Dependency Injection:
        Instantiated by the orchestrator with a run_id and output directory.

    Example::

        edf_log = EDFLogger(
            run_id="edf_2026-06-27_001",
            log_dir=Path("./CONTENT/.edf/logs"),
            level=logging.INFO,
        )
        logger = edf_log.get_logger("download")
        logger.info("File downloaded successfully", extra={
            "details": {"file": "maths.pdf", "size": 123456}
        })
        edf_log.shutdown()
    """

    def __init__(
        self,
        run_id: str = "",
        log_dir: Optional[Path | str] = None,
        level: int = logging.INFO,
        console_enabled: bool = True,
        file_enabled: bool = True,
        jsonl_enabled: bool = True,
    ) -> None:
        """
        Initialize the EDF logger.

        Args:
            run_id: Unique identifier for this pipeline run.
            log_dir: Directory for log files. None disables file logging.
            level: Logging level (e.g., logging.INFO).
            console_enabled: Whether to log to console.
            file_enabled: Whether to write .log file.
            jsonl_enabled: Whether to write .jsonl file.
        """
        self._run_id = run_id or self._generate_run_id()
        self._log_dir = Path(log_dir) if log_dir else None
        self._level = level
        self._console_enabled = console_enabled
        self._file_enabled = file_enabled and log_dir is not None
        self._jsonl_enabled = jsonl_enabled and log_dir is not None

        self._root_logger: Optional[logging.Logger] = None
        self._log_file_path: Optional[Path] = None
        self._jsonl_file_path: Optional[Path] = None
        self._handlers: list[logging.Handler] = []

        self._setup()

    def _generate_run_id(self) -> str:
        """Generate a default run ID based on current timestamp."""
        now = datetime.now()
        return f"edf_{now.strftime('%Y-%m-%d_%H%M%S')}"

    def _setup(self) -> None:
        """
        Configure the logging stack: console, file, and JSONL handlers.

        Creates the log directory if needed.
        """
        # Ensure log directory exists
        if self._log_dir:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            self._log_file_path = self._log_dir / f"{self._run_id}.log"
            self._jsonl_file_path = self._log_dir / f"{self._run_id}.jsonl"

        # Root logger for EDF
        self._root_logger = logging.getLogger("edf")
        self._root_logger.setLevel(self._level)

        # Prevent duplicate handlers on re-initialization
        if self._root_logger.handlers:
            self._root_logger.handlers.clear()

        # Console handler — human-readable
        if self._console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._level)
            console_fmt = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler.setFormatter(console_fmt)
            self._root_logger.addHandler(console_handler)
            self._handlers.append(console_handler)

        # File handler — human-readable .log
        if self._file_enabled and self._log_file_path:
            file_handler = logging.FileHandler(
                str(self._log_file_path), encoding="utf-8"
            )
            file_handler.setLevel(self._level)
            file_fmt = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_fmt)
            self._root_logger.addHandler(file_handler)
            self._handlers.append(file_handler)

        # JSONL handler — machine-readable
        if self._jsonl_enabled and self._jsonl_file_path:
            jsonl_handler = logging.FileHandler(
                str(self._jsonl_file_path), encoding="utf-8"
            )
            jsonl_handler.setLevel(self._level)
            jsonl_handler.setFormatter(JSONFormatter(run_id=self._run_id))
            self._root_logger.addHandler(jsonl_handler)
            self._handlers.append(jsonl_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a named logger under the EDF hierarchy.

        Args:
            name: Logger name (e.g., "download", "verify", "storage").

        Returns:
            A child logger under the "edf" namespace.
        """
        return logging.getLogger(f"edf.{name}")

    def shutdown(self) -> None:
        """
        Flush and close all log handlers.

        Call this at the end of each pipeline run.
        """
        if self._root_logger:
            for handler in self._handlers:
                try:
                    handler.flush()
                    handler.close()
                except Exception:
                    pass
            self._root_logger.handlers.clear()
            self._handlers.clear()

    @property
    def run_id(self) -> str:
        """Return the run identifier."""
        return self._run_id

    @property
    def log_file_path(self) -> Optional[Path]:
        """Return path to the human-readable log file, or None."""
        return self._log_file_path

    @property
    def jsonl_file_path(self) -> Optional[Path]:
        """Return path to the JSONL log file, or None."""
        return self._jsonl_file_path

    def __repr__(self) -> str:
        return f"EDFLogger(run_id={self._run_id!r})"
