"""
EDF-L1 Base Adapter.

Abstract base class defining the adapter interface for all source boards.
Each board (GSEB, NCERT, ...) implements this interface to provide
download descriptors and pre-flight verification.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.edf.models.data import DownloadDescriptor, PreflightIssue


class BaseAdapter(ABC):
    """
    Abstract base adapter for education content sources.

    Every source board must implement this interface. The lifecycle is:

    1. ``pre_flight()`` — Validate configuration, verify codes (NCERT),
       check URL reachability (GSEB). Returns issues; raises on fatal errors.
    2. ``get_descriptors()`` — Yield ``DownloadDescriptor`` objects for all
       configured textbooks. Called only after successful pre-flight.
    3. ``resolve_url(descriptor)`` — Optionally transform the descriptor's URL
       into a final download URL (e.g., code → URL pattern for NCERT).

    Dependency Injection:
        Subclasses receive their configuration dict via ``__init__``.
        An ``http_client`` (optional) may be injected for pre-flight checks.

    Example::

        class MyAdapter(BaseAdapter):
            def __init__(self, config: dict, http_client=None):
                self._config = config["my_board"]
                self._http = http_client

            def pre_flight(self) -> List[PreflightIssue]:
                ...

            def get_descriptors(self) -> List[DownloadDescriptor]:
                ...

            def resolve_url(self, descriptor: DownloadDescriptor) -> str:
                ...

            @property
            def board_name(self) -> str:
                return "MY_BOARD"
    """

    def __init__(self, config: dict, http_client=None) -> None:
        """
        Initialize the adapter.

        Args:
            config: Board-specific configuration dictionary.
            http_client: Optional HTTP client for pre-flight checks.
        """
        self._config = config
        self._http = http_client

    @property
    @abstractmethod
    def board_name(self) -> str:
        """
        Return the canonical board identifier string.

        Returns:
            Board name (e.g., "GSEB", "NCERT").
        """
        ...

    @abstractmethod
    def pre_flight(self) -> List[PreflightIssue]:
        """
        Run pre-flight verification checks.

        For NCERT: fetch master-list, verify textbook codes.
        For GSEB: validate URL format, check required fields.

        Returns:
            List of pre-flight issues (warnings, info). Empty list means clean.

        Raises:
            PreflightError: On fatal issues that should abort the pipeline.
        """
        ...

    @abstractmethod
    def get_descriptors(self) -> List[DownloadDescriptor]:
        """
        Produce download descriptors for all configured textbooks.

        Called only after ``pre_flight()`` succeeds.

        Returns:
            List of ``DownloadDescriptor`` objects ready for the download pipeline.
        """
        ...

    @abstractmethod
    def resolve_url(self, descriptor: DownloadDescriptor) -> str:
        """
        Resolve the final download URL for a descriptor.

        For GSEB: returns the URL directly from config (placeholder).
        For NCERT: may construct URL from code pattern.

        Args:
            descriptor: The descriptor to resolve a URL for.

        Returns:
            Final HTTP(S) download URL.
        """
        ...
