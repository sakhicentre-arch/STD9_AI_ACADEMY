"""
EDF-L1 Data Models.

Defines all dataclasses and enums used across the framework.
These are the canonical type definitions — other modules import from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Board(str, Enum):
    """Supported education boards."""
    GSEB = "GSEB"
    NCERT = "NCERT"


class ValidationStatus(str, Enum):
    """Result of file validation gates."""
    VALID = "VALID"
    INVALID_HEADER = "INVALID_HEADER"
    INVALID_SIZE = "INVALID_SIZE"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    SKIPPED = "SKIPPED"
    CONFLICT = "CONFLICT"


class PreflightSeverity(str, Enum):
    """Severity of a pre-flight verification issue."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DownloadDescriptor:
    """
    Represents a single file to download.

    This is the primary data object passed between adapters and the
    download pipeline. Every field is immutable once created.

    Attributes:
        board: Source board identifier (GSEB or NCERT).
        std: Grade/standard (e.g., "09").
        subject: Subject name (e.g., "maths").
        medium: Instruction medium (e.g., "gujarati", "english").
        language: ISO language code (e.g., "gu", "en").
        url: Direct download URL for the PDF.
        filename: Target filename for local storage.
        expected_sha256: Optional pre-known SHA-256 for validation.
        expected_size_bytes: Optional expected file size for validation.
        metadata: Additional key-value metadata from the adapter.
    """
    board: str
    std: str
    subject: str
    medium: str
    language: str
    url: str
    filename: str
    expected_sha256: Optional[str] = None
    expected_size_bytes: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """
    Result of validating a downloaded file.

    Attributes:
        status: Overall validation outcome.
        file_path: Absolute path to the validated file.
        sha256: Computed SHA-256 checksum.
        size_bytes: File size in bytes.
        details: Additional context about the validation result.
        timestamp: When validation occurred.
    """
    status: ValidationStatus
    file_path: str
    sha256: str
    size_bytes: int
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ManifestEntry:
    """
    Single entry in the manifest.json file.

    Attributes:
        path: Relative path from CONTENT root.
        sha256: SHA-256 checksum of the file.
        size_bytes: File size in bytes.
        board: Source board identifier.
        subject: Subject name.
        medium: Instruction medium.
        std: Grade/standard.
        language: Language code.
        source_url: Original download URL (if known).
        downloaded_at: ISO timestamp of download.
        last_verified: ISO timestamp of last verification.
        validation_status: Last known validation status.
        managed: Whether EDF manages this file.
    """
    path: str
    sha256: str
    size_bytes: int
    board: str
    subject: str
    medium: str
    std: str
    language: str
    source_url: Optional[str] = None
    downloaded_at: Optional[str] = None
    last_verified: Optional[str] = None
    validation_status: str = ValidationStatus.VALID.value
    managed: bool = True


@dataclass
class PreflightIssue:
    """
    A single pre-flight verification finding.

    Attributes:
        severity: How serious the issue is.
        code: Machine-readable issue code.
        message: Human-readable description.
        context: Additional key-value context.
    """
    severity: PreflightSeverity
    code: str
    message: str
    context: dict = field(default_factory=dict)


@dataclass
class RunSummary:
    """
    Summary of a single EDF-L1 pipeline run.

    Attributes:
        run_id: Unique identifier for this run.
        start_time: ISO timestamp when the run started.
        end_time: ISO timestamp when the run ended.
        duration_seconds: Total wall-clock duration.
        attempted: Total files the pipeline attempted to process.
        succeeded: Files downloaded and validated successfully.
        skipped: Files skipped due to duplicate detection.
        failed: Files that failed download or validation.
        board_summaries: Per-board breakdown of results.
        exit_code: Process exit code (0=success, 1=partial, 2=fatal).
    """
    run_id: str
    start_time: str
    end_time: str = ""
    duration_seconds: float = 0.0
    attempted: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    board_summaries: dict = field(default_factory=dict)
    exit_code: int = 0
