"""
EDF-L1 GSEB Adapter.

Produces DownloadDescriptor objects for GSEB (Gujarat Secondary and Higher
Secondary Education Board) textbooks.  Validates configuration, checks URL
reachability, and yields descriptors for the download pipeline.

Configuration expected under config["gseb"]::

    gseb:
      textbooks:
        - std: "09"
          subject: "maths"
          medium: "gujarati"
          language: "gu"
          url: "https://..."
          filename: "std09_gujarati_maths.pdf"
          expected_sha256: null   # optional
          expected_size_bytes: null  # optional
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.edf.adapters.base import BaseAdapter
from src.edf.models.data import DownloadDescriptor, PreflightIssue, PreflightSeverity
from src.edf.utils.http import head_request

logger = logging.getLogger(__name__)


class GSEBAdapter(BaseAdapter):
    """
    Adapter for GSEB board textbooks.

    Reads textbook entries from the ``gseb.textbooks`` configuration section
    and produces ``DownloadDescriptor`` objects.  Supports pre-flight URL
    reachability checks and validates required configuration fields.

    Dependency Injection:
        ``config`` dict is supplied by the orchestrator via ConfigLoader.
        ``http_client`` is currently unused; URL checks use the utility
        ``head_request`` function directly.

    Example::

        adapter = GSEBAdapter(config={"gseb": {"textbooks": [...]}})
        issues = adapter.pre_flight()
        descriptors = adapter.get_descriptors()
    """

    def __init__(self, config: dict, http_client=None) -> None:
        """
        Initialize the GSEB adapter.

        Args:
            config: Full configuration dict; the adapter reads config["gseb"].
            http_client: Optional HTTP client (reserved for future use).
        """
        super().__init__(config, http_client)
        # The board-specific sub-dict may not exist (empty config).
        self._board_config: dict = config.get("gseb", {})
        self._textbooks: List[dict] = self._board_config.get("textbooks", [])
        self._download_config: dict = config.get("download", {})

    # ------------------------------------------------------------------
    # BaseAdapter interface
    # ------------------------------------------------------------------

    @property
    def board_name(self) -> str:
        """Return the canonical board identifier."""
        return "GSEB"

    def pre_flight(self) -> List[PreflightIssue]:
        """
        Run pre-flight verification for the GSEB adapter.

        Checks:
            1. Configuration structure has the ``textbooks`` list.
            2. Each textbook entry has the required fields (std, subject,
               medium, language, url, filename).
            3. URL format is valid (starts with http:// or https://).
            4. URL reachability via HEAD request (non-fatal warning).

        Returns:
            List of PreflightIssue objects (warnings/info). Empty on clean.
        """
        issues: List[PreflightIssue] = []

        # --- Check config structure ---
        if not self._textbooks:
            issues.append(PreflightIssue(
                severity=PreflightSeverity.WARNING,
                code="GSEB_NO_TEXTBOOKS",
                message="No textbooks configured for GSEB board.",
                context={"board": "GSEB"},
            ))
            return issues

        logger.info(
            "GSEB pre-flight: %d textbook(s) configured",
            len(self._textbooks),
        )

        # --- Per-textbook validation ---
        required_fields = ["std", "subject", "medium", "language", "url", "filename"]

        for idx, tb in enumerate(self._textbooks):
            prefix = f"textbook[{idx}]"

            # Check required fields
            missing = [f for f in required_fields if not tb.get(f)]
            if missing:
                issues.append(PreflightIssue(
                    severity=PreflightSeverity.ERROR,
                    code="GSEB_MISSING_FIELDS",
                    message=f"{prefix}: missing fields: {', '.join(missing)}",
                    context={"index": idx, "missing_fields": missing},
                ))
                continue  # Cannot validate URL without config

            # Validate URL format
            url = tb["url"]
            if not url.startswith(("http://", "https://")):
                issues.append(PreflightIssue(
                    severity=PreflightSeverity.ERROR,
                    code="GSEB_INVALID_URL",
                    message=f"{prefix}: URL must start with http(s)://: {url}",
                    context={"index": idx, "url": url},
                ))
                continue

            # URL reachability check (non-fatal)
            timeout = self._download_config.get("timeout_seconds", 30)
            head_result = head_request(url, timeout=timeout)
            if head_result is None:
                issues.append(PreflightIssue(
                    severity=PreflightSeverity.WARNING,
                    code="GSEB_URL_UNREACHABLE",
                    message=f"{prefix}: HEAD request failed for {url}",
                    context={"index": idx, "url": url},
                ))
            elif head_result["status_code"] >= 400:
                issues.append(PreflightIssue(
                    severity=PreflightSeverity.WARNING,
                    code="GSEB_URL_HTTP_ERROR",
                    message=(
                        f"{prefix}: HEAD returned {head_result['status_code']} "
                        f"for {url}"
                    ),
                    context={
                        "index": idx,
                        "url": url,
                        "status_code": head_result["status_code"],
                    },
                ))
            else:
                logger.debug(
                    "GSEB pre-flight: %s reachable (HTTP %d)",
                    url,
                    head_result["status_code"],
                )

            # Log discovery
            logger.info(
                "GSEB discovered: %s -> %s (%s, %s)",
                tb.get("filename", "?"),
                url,
                tb.get("std", "?"),
                tb.get("medium", "?"),
            )

        error_count = sum(
            1 for i in issues if i.severity == PreflightSeverity.ERROR
        )
        if error_count:
            logger.warning(
                "GSEB pre-flight: %d error(s), %d warning(s)",
                error_count,
                len(issues) - error_count,
            )
        else:
            logger.info("GSEB pre-flight: all checks passed")

        return issues

    def get_descriptors(self) -> List[DownloadDescriptor]:
        """
        Produce download descriptors for all configured GSEB textbooks.

        Only textbook entries with valid configuration (all required fields
        present) are included. Entries that failed pre-flight field
        validation are silently skipped.

        Returns:
            List of DownloadDescriptor objects.
        """
        required_fields = ["std", "subject", "medium", "language", "url", "filename"]
        descriptors: List[DownloadDescriptor] = []

        for tb in self._textbooks:
            # Skip entries missing required fields
            if any(not tb.get(f) for f in required_fields):
                logger.warning(
                    "Skipping GSEB textbook with missing fields: %s",
                    tb.get("filename", "<unknown>"),
                )
                continue

            descriptor = DownloadDescriptor(
                board=self.board_name,
                std=str(tb["std"]),
                subject=str(tb["subject"]),
                medium=str(tb["medium"]),
                language=str(tb["language"]),
                url=str(tb["url"]),
                filename=str(tb["filename"]),
                expected_sha256=tb.get("expected_sha256"),
                expected_size_bytes=tb.get("expected_size_bytes"),
                metadata={
                    "adapter": "GSEB",
                    "title": tb.get("title", ""),
                    "publisher": tb.get("publisher", "GSEB"),
                    "academic_year": tb.get("academic_year", ""),
                },
            )
            descriptors.append(descriptor)
            logger.debug(
                "GSEB descriptor: %s (%s/%s)",
                descriptor.filename,
                descriptor.std,
                descriptor.subject,
            )

        logger.info(
            "GSEB: produced %d descriptor(s)", len(descriptors)
        )
        return descriptors

    def resolve_url(self, descriptor: DownloadDescriptor) -> str:
        """
        Resolve the final download URL for a GSEB descriptor.

        GSEB URLs are direct links stored in the configuration, so this
        method returns the URL unchanged.

        Args:
            descriptor: The descriptor to resolve.

        Returns:
            The URL string from the descriptor.
        """
        return descriptor.url
