"""
EDF-L1 Download Pipeline.

Orchestrates the per-file download workflow:
  duplicate check → download → validate → atomic store → manifest register.

Each file is processed independently so that a single failure does not
abort the entire run.  Results are aggregated into a RunSummary.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.edf.models.data import (
    DownloadDescriptor,
    ManifestEntry,
    PreflightIssue,
    RunSummary,
    ValidationStatus,
    ValidationResult,
)
from src.edf.storage.manager import StorageManager
from src.edf.utils.hashing import compare_checksums, sha256_file
from src.edf.utils.http import download_stream
from src.edf.utils.pdf import validate_pdf_header, validate_pdf_size

logger = logging.getLogger(__name__)


class DownloadPipeline:
    """
    Processes a list of DownloadDescriptor objects end-to-end.

    For each descriptor the pipeline executes:

    1. **Duplicate check** — skip if the file already exists with the same
       checksum (incremental behaviour).
    2. **Download** — stream to a temp file with retry and timeout.
    3. **Validation** — verify PDF header, file size, and optional checksum.
    4. **Atomic store** — place the temp file at its canonical path via
       StorageManager.
    5. **Manifest registration** — add a ManifestEntry and register the
       checksum.

    Failures for individual files are recorded but do not halt the pipeline.

    Dependency Injection:
        Receives StorageManager, ManifestManager, and download configuration
        via the constructor.

    Example::

        pipeline = DownloadPipeline(
            storage_manager=storage,
            manifest_manager=manifest,
            config={"download": {"max_retries": 3}},
        )
        summary = pipeline.run(descriptors, run_id="run_001")
    """

    def __init__(
        self,
        storage_manager: StorageManager,
        manifest_manager: Any,
        config: dict,
    ) -> None:
        """
        Initialize the download pipeline.

        Args:
            storage_manager: StorageManager for path resolution and file placement.
            manifest_manager: ManifestManager for entry registration.
            config: Full configuration dict (used for download/validation settings).
        """
        self._storage = storage_manager
        self._manifest = manifest_manager
        self._download_cfg = config.get("download", {})
        self._validation_cfg = config.get("validation", {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        descriptors: List[DownloadDescriptor],
        run_id: str = "",
        force: bool = False,
    ) -> RunSummary:
        """
        Process all descriptors and produce a run summary.

        Args:
            descriptors: List of DownloadDescriptor objects to process.
            run_id: Identifier for this pipeline run.
            force: If True, overwrite existing files (--force semantics).

        Returns:
            RunSummary with aggregated results.
        """
        start_time = datetime.now().isoformat()
        t0 = time.monotonic()

        summary = RunSummary(
            run_id=run_id,
            start_time=start_time,
        )

        for descriptor in descriptors:
            result = self._process_descriptor(descriptor, force=force)
            summary.attempted += 1

            status_key = result["status"]
            if status_key == "skipped":
                summary.skipped += 1
            elif status_key == "succeeded":
                summary.succeeded += 1
            else:
                summary.failed += 1

            # Per-board breakdown: aggregate counts per descriptor.board so each
            # board (GSEB, NCERT, ...) gets accurate numbers. The bucket is
            # created on first sight of a board.
            bucket = summary.board_summaries.setdefault(
                descriptor.board,
                {"attempted": 0, "succeeded": 0, "skipped": 0, "failed": 0},
            )
            bucket["attempted"] += 1
            bucket[status_key] += 1

        elapsed = time.monotonic() - t0
        summary.end_time = datetime.now().isoformat()
        summary.duration_seconds = round(elapsed, 3)
        summary.exit_code = 2 if summary.failed == summary.attempted else (
            1 if summary.failed > 0 else 0
        )

        logger.info(
            "Download pipeline complete: %d attempted, %d succeeded, "
            "%d skipped, %d failed (%.1fs)",
            summary.attempted,
            summary.succeeded,
            summary.skipped,
            summary.failed,
            elapsed,
        )
        return summary

    # ------------------------------------------------------------------
    # Internal: single descriptor processing
    # ------------------------------------------------------------------

    def _process_descriptor(
        self,
        descriptor: DownloadDescriptor,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a single descriptor through the full pipeline.

        Returns a result dict with keys: status, descriptor, details.
        """
        target_path = self._storage.resolve_path(
            board=descriptor.board,
            std=descriptor.std,
            subject=descriptor.subject,
            medium=descriptor.medium,
            filename=descriptor.filename,
        )
        rel_path = self._storage.to_relative_path(target_path)

        logger.info(
            "Processing: %s (%s/%s/%s)",
            descriptor.filename,
            descriptor.board,
            descriptor.std,
            descriptor.subject,
        )

        # --- Step 1: Duplicate / incremental check ---
        if not force and self._storage.file_exists(target_path):
            existing_checksum = self._storage.get_checksum(target_path)
            if existing_checksum:
                # File exists with a known checksum — skip unless force.
                logger.info(
                    "Skipping (exists): %s (sha256=%s)",
                    descriptor.filename,
                    existing_checksum[:16],
                )
                return {
                    "status": "skipped",
                    "descriptor": descriptor,
                    "details": {
                        "reason": "file_exists",
                        "existing_checksum": existing_checksum,
                        "path": str(target_path),
                    },
                }

        # --- Step 2: Download to temp file ---
        temp_path = self._storage.create_temp_path(descriptor.filename)
        max_retries = self._download_cfg.get("max_retries", 3)
        timeout = self._download_cfg.get("timeout_seconds", 120)
        chunk_size = self._download_cfg.get("chunk_size", 8192)

        dl_result = download_stream(
            url=descriptor.url,
            dest_path=str(temp_path),
            chunk_size=chunk_size,
            timeout=timeout,
            max_retries=max_retries,
        )

        if not dl_result["success"]:
            self._storage.cleanup_temp(temp_path)
            error_detail = dl_result.get("error", "unknown")
            logger.error(
                "Download failed: %s -> %s",
                descriptor.filename,
                error_detail,
            )
            return {
                "status": "failed",
                "descriptor": descriptor,
                "details": {
                    "reason": "download_failed",
                    "error": error_detail,
                    "status_code": dl_result.get("status_code", 0),
                },
            }

        logger.info(
            "Downloaded: %s (%d bytes, attempt info available)",
            descriptor.filename,
            dl_result["size_bytes"],
        )

        # --- Step 3: Validation ---
        validation = self._validate_download(
            temp_path=temp_path,
            descriptor=descriptor,
        )

        if validation.status != ValidationStatus.VALID:
            self._storage.cleanup_temp(temp_path)
            logger.error(
                "Validation failed: %s -> %s",
                descriptor.filename,
                validation.status.value,
            )
            return {
                "status": "failed",
                "descriptor": descriptor,
                "details": {
                    "reason": "validation_failed",
                    "validation_status": validation.status.value,
                    "validation_details": validation.details,
                },
            }

        # --- Step 4: Atomic placement ---
        try:
            place_report = self._storage.atomic_place(
                temp_path=temp_path,
                target_path=target_path,
                force=force,
            )
        except OSError as exc:
            logger.error(
                "Atomic placement failed: %s -> %s",
                descriptor.filename,
                exc,
            )
            return {
                "status": "failed",
                "descriptor": descriptor,
                "details": {
                    "reason": "placement_failed",
                    "error": str(exc),
                },
            }

        # Handle conflict (file appeared between duplicate check and placement)
        if place_report.get("conflict"):
            logger.warning(
                "Conflict: %s already exists at %s",
                descriptor.filename,
                target_path,
            )
            return {
                "status": "skipped",
                "descriptor": descriptor,
                "details": {
                    "reason": "conflict",
                    "path": str(target_path),
                },
            }

        # --- Step 5: Manifest registration ---
        placed_sha = place_report.get("sha256", "")
        placed_size = place_report.get("size_bytes", 0)
        now_iso = datetime.now().isoformat()

        rel = self._storage.to_relative_path(target_path)
        if rel is None:
            rel = str(target_path)

        entry = ManifestEntry(
            path=rel,
            sha256=placed_sha,
            size_bytes=placed_size,
            board=descriptor.board,
            subject=descriptor.subject,
            medium=descriptor.medium,
            std=descriptor.std,
            language=descriptor.language,
            source_url=descriptor.url,
            downloaded_at=now_iso,
            last_verified=now_iso,
            validation_status=ValidationStatus.VALID.value,
            managed=True,
        )
        self._manifest.add_entry(entry)
        self._manifest.add_checksum(placed_sha, rel)

        # Register in StorageManager's checksum registry too.
        self._storage.register_checksum(placed_sha, target_path)

        logger.info(
            "Registered: %s (sha256=%s, size=%d)",
            descriptor.filename,
            placed_sha[:16],
            placed_size,
        )

        return {
            "status": "succeeded",
            "descriptor": descriptor,
            "details": {
                "path": str(target_path),
                "sha256": placed_sha,
                "size_bytes": placed_size,
                "rel_path": rel,
            },
        }

    # ------------------------------------------------------------------
    # Internal: validation
    # ------------------------------------------------------------------

    def _validate_download(
        self,
        temp_path: Path,
        descriptor: DownloadDescriptor,
    ) -> ValidationResult:
        """
        Validate a downloaded temp file.

        Checks (in order):
            1. PDF header magic bytes (``%PDF-``).
            2. File size constraints.
            3. SHA-256 checksum (if expected_sha256 is configured).

        Args:
            temp_path: Path to the downloaded temp file.
            descriptor: Original descriptor with expected metadata.

        Returns:
            ValidationResult with status and details.
        """
        # --- PDF header check ---
        if not validate_pdf_header(temp_path):
            return ValidationResult(
                status=ValidationStatus.INVALID_HEADER,
                file_path=str(temp_path),
                sha256="",
                size_bytes=0,
                details={"reason": "File does not start with %PDF- header"},
            )

        # --- Size check ---
        min_size = self._validation_cfg.get("min_size_bytes", 10240)
        max_size = self._validation_cfg.get("max_size_bytes")

        # Descriptor-level expected_size overrides global config.
        expected_size = descriptor.expected_size_bytes

        if expected_size is not None:
            if not validate_pdf_size(
                temp_path,
                min_bytes=expected_size,
                max_bytes=expected_size,
            ):
                return ValidationResult(
                    status=ValidationStatus.INVALID_SIZE,
                    file_path=str(temp_path),
                    sha256="",
                    size_bytes=0,
                    details={
                        "reason": (
                            f"File size does not match expected "
                            f"{expected_size} bytes"
                        ),
                    },
                )
        else:
            if not validate_pdf_size(temp_path, min_bytes=min_size, max_bytes=max_size):
                return ValidationResult(
                    status=ValidationStatus.INVALID_SIZE,
                    file_path=str(temp_path),
                    sha256="",
                    size_bytes=0,
                    details={
                        "reason": (
                            f"File size below minimum {min_size} bytes "
                            f"(or above max {max_size})"
                        ),
                    },
                )

        # --- Checksum check ---
        computed_sha = sha256_file(temp_path)
        if not compare_checksums(
            computed_sha,
            descriptor.expected_sha256,
        ):
            return ValidationResult(
                status=ValidationStatus.CHECKSUM_MISMATCH,
                file_path=str(temp_path),
                sha256=computed_sha,
                size_bytes=temp_path.stat().st_size,
                details={
                    "reason": (
                        f"SHA-256 mismatch: computed={computed_sha[:16]}..., "
                        f"expected={descriptor.expected_sha256[:16] if descriptor.expected_sha256 else 'N/A'}"
                    ),
                },
            )

        # --- All checks passed ---
        file_size = temp_path.stat().st_size
        return ValidationResult(
            status=ValidationStatus.VALID,
            file_path=str(temp_path),
            sha256=computed_sha,
            size_bytes=file_size,
            details={"validation_gates": ["header", "size", "checksum"]},
        )
