"""
EDF-L1 NCERT Adapter.

Produces DownloadDescriptor objects for NCERT (National Council of Educational
Research and Training) textbooks. NCERT identifies books by a textbook *code*
(e.g. ``IEMH1``) rather than a direct URL, so this adapter resolves a download
URL and filename from configurable templates, while still honouring explicit
``url`` / ``filename`` overrides on individual entries.

Configuration expected under config["ncert"]::

    ncert:
      enabled: true
      master_list_url: "https://ncert.nic.in/..."        # informational
      url_template: "https://ncert.nic.in/textbook/pdf/{code}.pdf"
      filename_template: "{std}_{medium}_{subject}_{code}.pdf"
      textbooks:
        - code: "IEMH1"                                  # required
          std: "09"                                      # required
          subject: "maths"                               # required
          medium: "english"                              # required
          language: "en"                                 # required
          part: "complete"                               # optional: chapter|complete
          url: ""                                        # optional override
          filename: ""                                   # optional override
          expected_sha256: null                          # optional
          expected_size_bytes: null                      # optional
          title: ""                                      # optional
          academic_year: ""                              # optional

The behavioural contract mirrors :class:`GSEBAdapter` exactly: same pre-flight
severity model, same issue-code conventions (``NCERT_*``), and the same
descriptor metadata keys.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from src.edf.adapters.base import BaseAdapter
from src.edf.models.data import DownloadDescriptor, PreflightIssue, PreflightSeverity
from src.edf.utils.http import head_request

logger = logging.getLogger(__name__)

# Default templates for URL/filename derivation from a textbook code.
DEFAULT_URL_TEMPLATE = "https://ncert.nic.in/textbook/pdf/{code}.pdf"
DEFAULT_FILENAME_TEMPLATE = "{std}_{medium}_{subject}_{code}.pdf"

# Required per-entry fields. Note: ``url`` and ``filename`` are NOT required —
# they are derived from templates when absent (the defining difference from GSEB).
REQUIRED_FIELDS = ["code", "std", "subject", "medium", "language"]

# Characters allowed in derived filenames. Everything else is replaced with "_".
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_filename(name: str) -> str:
    """Return a filesystem-safe filename.

    Path separators and other unsafe characters are replaced with ``_``. This
    mirrors the sanitization intent of StorageManager without coupling the
    adapter to the storage layer.
    """
    if not name:
        return name
    # Collapse any path separators first, then strip remaining unsafe chars.
    name = name.replace("\\", "/").split("/")[-1]
    return _FILENAME_SAFE.sub("_", name)


class NCERTAdapter(BaseAdapter):
    """
    Adapter for NCERT board textbooks.

    Reads textbook entries from the ``ncert.textbooks`` configuration section.
    Each entry is identified by a textbook ``code``; the download URL and target
    filename are resolved from configurable templates (overridable per entry).
    Supports pre-flight URL reachability checks and validates required fields.

    Dependency Injection:
        ``config`` dict is supplied by the orchestrator via ConfigLoader.
        ``http_client`` is currently unused; URL checks use the utility
        ``head_request`` function directly.

    Example::

        adapter = NCERTAdapter(config={"ncert": {"textbooks": [...]}})
        issues = adapter.pre_flight()
        descriptors = adapter.get_descriptors()
    """

    def __init__(self, config: dict, http_client=None) -> None:
        """
        Initialize the NCERT adapter.

        Args:
            config: Full configuration dict; the adapter reads config["ncert"].
            http_client: Optional HTTP client (reserved for future use).
        """
        super().__init__(config, http_client)
        # The board-specific sub-dict may not exist (empty config).
        self._board_config: dict = config.get("ncert", {})
        self._textbooks: List[dict] = self._board_config.get("textbooks", [])
        self._download_config: dict = config.get("download", {})
        # Board-level derivation templates / metadata.
        self._url_template: str = self._board_config.get(
            "url_template", DEFAULT_URL_TEMPLATE
        )
        self._filename_template: str = self._board_config.get(
            "filename_template", DEFAULT_FILENAME_TEMPLATE
        )
        self._master_list_url: Optional[str] = self._board_config.get(
            "master_list_url"
        )

    # ------------------------------------------------------------------
    # BaseAdapter interface
    # ------------------------------------------------------------------

    @property
    def board_name(self) -> str:
        """Return the canonical board identifier."""
        return "NCERT"

    # ------------------------------------------------------------------
    # Internal: URL / filename resolution
    # ------------------------------------------------------------------

    def _format_context(self, tb: dict) -> dict:
        """Build a substitution context for the URL/filename templates."""
        return {
            "code": str(tb.get("code", "")),
            "std": str(tb.get("std", "")),
            "subject": str(tb.get("subject", "")),
            "medium": str(tb.get("medium", "")),
            "language": str(tb.get("language", "")),
        }

    def _resolve_url(self, tb: dict) -> str:
        """Resolve the download URL for a textbook entry.

        An explicit ``url`` override always wins. Otherwise the board-level
        ``url_template`` is expanded with the entry's fields.
        """
        explicit = tb.get("url")
        if explicit:
            return str(explicit)
        try:
            return self._url_template.format(**self._format_context(tb))
        except KeyError:
            # Template referenced an unknown key; fall back to raw template.
            return self._url_template

    def _resolve_filename(self, tb: dict) -> str:
        """Resolve the target filename for a textbook entry.

        An explicit ``filename`` override always wins (after sanitization).
        Otherwise the board-level ``filename_template`` is expanded.
        """
        explicit = tb.get("filename")
        if explicit:
            return _sanitize_filename(str(explicit))
        try:
            return _sanitize_filename(
                self._filename_template.format(**self._format_context(tb))
            )
        except KeyError:
            return _sanitize_filename(self._filename_template)

    # ------------------------------------------------------------------
    # BaseAdapter interface
    # ------------------------------------------------------------------

    def pre_flight(self) -> List[PreflightIssue]:
        """
        Run pre-flight verification for the NCERT adapter.

        Checks:
            1. Configuration structure has the ``textbooks`` list.
            2. Each entry has the required fields (code, std, subject,
               medium, language).
            3. Resolved URL format is valid (starts with http:// or https://).
            4. URL reachability via HEAD request (non-fatal warning).

        Returns:
            List of PreflightIssue objects (warnings/info). Empty on clean.
        """
        issues: List[PreflightIssue] = []

        # --- Check config structure ---
        if not self._textbooks:
            issues.append(PreflightIssue(
                severity=PreflightSeverity.WARNING,
                code="NCERT_NO_TEXTBOOKS",
                message="No textbooks configured for NCERT board.",
                context={"board": "NCERT"},
            ))
            return issues

        logger.info(
            "NCERT pre-flight: %d textbook(s) configured",
            len(self._textbooks),
        )

        # --- Per-textbook validation ---
        for idx, tb in enumerate(self._textbooks):
            prefix = f"textbook[{idx}]"

            # Check required fields
            missing = [f for f in REQUIRED_FIELDS if not tb.get(f)]
            if missing:
                issues.append(PreflightIssue(
                    severity=PreflightSeverity.ERROR,
                    code="NCERT_MISSING_FIELDS",
                    message=f"{prefix}: missing fields: {', '.join(missing)}",
                    context={"index": idx, "missing_fields": missing},
                ))
                continue  # Cannot validate URL without config

            # Validate resolved URL format
            url = self._resolve_url(tb)
            if not url.startswith(("http://", "https://")):
                issues.append(PreflightIssue(
                    severity=PreflightSeverity.ERROR,
                    code="NCERT_INVALID_URL",
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
                    code="NCERT_URL_UNREACHABLE",
                    message=f"{prefix}: HEAD request failed for {url}",
                    context={"index": idx, "url": url},
                ))
            elif head_result["status_code"] >= 400:
                issues.append(PreflightIssue(
                    severity=PreflightSeverity.WARNING,
                    code="NCERT_URL_HTTP_ERROR",
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
                    "NCERT pre-flight: %s reachable (HTTP %d)",
                    url,
                    head_result["status_code"],
                )

            # Log discovery
            logger.info(
                "NCERT discovered: %s -> %s (%s, %s)",
                tb.get("code", "?"),
                url,
                tb.get("std", "?"),
                tb.get("medium", "?"),
            )

        error_count = sum(
            1 for i in issues if i.severity == PreflightSeverity.ERROR
        )
        if error_count:
            logger.warning(
                "NCERT pre-flight: %d error(s), %d warning(s)",
                error_count,
                len(issues) - error_count,
            )
        else:
            logger.info("NCERT pre-flight: all checks passed")

        return issues

    def get_descriptors(self) -> List[DownloadDescriptor]:
        """
        Produce download descriptors for all configured NCERT textbooks.

        Only entries with valid configuration (all required fields present)
        are included. Entries that failed field validation are silently
        skipped. URLs and filenames are resolved from templates (or explicit
        overrides) at this point.

        Returns:
            List of DownloadDescriptor objects.
        """
        descriptors: List[DownloadDescriptor] = []

        for tb in self._textbooks:
            # Skip entries missing required fields
            if any(not tb.get(f) for f in REQUIRED_FIELDS):
                logger.warning(
                    "Skipping NCERT textbook with missing fields: %s",
                    tb.get("code", "<unknown>"),
                )
                continue

            resolved_url = self._resolve_url(tb)
            resolved_filename = self._resolve_filename(tb)

            descriptor = DownloadDescriptor(
                board=self.board_name,
                std=str(tb["std"]),
                subject=str(tb["subject"]),
                medium=str(tb["medium"]),
                language=str(tb["language"]),
                url=resolved_url,
                filename=resolved_filename,
                expected_sha256=tb.get("expected_sha256"),
                expected_size_bytes=tb.get("expected_size_bytes"),
                metadata={
                    "adapter": "NCERT",
                    "code": str(tb["code"]),
                    "title": tb.get("title", ""),
                    "publisher": tb.get("publisher", "NCERT"),
                    "academic_year": tb.get(
                        "academic_year",
                        self._board_config.get("academic_year", ""),
                    ),
                    "part": tb.get("part", ""),
                },
            )
            descriptors.append(descriptor)
            logger.debug(
                "NCERT descriptor: %s (%s/%s)",
                descriptor.filename,
                descriptor.std,
                descriptor.subject,
            )

        logger.info(
            "NCERT: produced %d descriptor(s)", len(descriptors)
        )
        return descriptors

    def resolve_url(self, descriptor: DownloadDescriptor) -> str:
        """
        Resolve the final download URL for an NCERT descriptor.

        NCERT URLs are fully resolved (template or override) at descriptor-build
        time, so this method returns the URL unchanged.

        Args:
            descriptor: The descriptor to resolve.

        Returns:
            The URL string from the descriptor.
        """
        return descriptor.url
