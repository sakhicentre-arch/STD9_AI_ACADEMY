"""
EDF-L1 Adapter Registry.

A central registry of source-board adapters. The registry is the **single
location** responsible for:

    - registering adapter *classes* keyed by board name
    - discovering which boards are registered
    - creating adapter *instances* on demand
    - determining which boards are enabled for a given configuration

The registry is intentionally a pure adapter-management component. It:

    - does NOT download files
    - does NOT orchestrate the pipeline
    - does NOT validate descriptors

It stores **classes**, not instances, so adapters are instantiated lazily only
when requested via :meth:`AdapterRegistry.create`.

Backward compatibility
----------------------
Existing flat configuration keys (``gseb``, ``ncert``, ``download``) continue to
work unchanged. Enable/disable flags are read from an **optional** top-level
``boards`` section::

    boards:
        gseb:
            enabled: true
        ncert:
            enabled: true

When the ``boards`` section (or a specific board's entry) is absent, the board
is treated as **enabled** — preserving Phase 5 behaviour.

Import rules
------------
This module MUST NOT import any of: the downloader, StorageManager,
ManifestManager, or the pipeline. To avoid a circular import with
:mod:`src.edf.adapters` (which re-exports adapters), the concrete adapter
classes are imported **lazily inside** :func:`default_registry`.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from src.edf.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Registry mapping board names to adapter classes.

    Stores ``board_name -> adapter_cls``. Instances are created lazily via
    :meth:`create` / :meth:`get`.

    Example::

        registry = AdapterRegistry()
        registry.register("GSEB", GSEBAdapter)
        registry.register("NCERT", NCERTAdapter)

        adapter = registry.create("GSEB", config=config)
        boards = AdapterRegistry.enabled_boards(config, registry.list_adapters())
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._adapters: Dict[str, Type[BaseAdapter]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, board_name: str, adapter_cls: Type[BaseAdapter]) -> None:
        """
        Register an adapter class for a board.

        Args:
            board_name: Canonical board identifier (e.g. ``"GSEB"``).
            adapter_cls: A concrete :class:`BaseAdapter` subclass.

        Raises:
            ValueError: If ``board_name`` is already registered.
            TypeError:  If ``adapter_cls`` is not a BaseAdapter subclass.
        """
        if not board_name or not isinstance(board_name, str):
            raise ValueError("board_name must be a non-empty string")
        if not isinstance(adapter_cls, type) or not issubclass(adapter_cls, BaseAdapter):
            raise TypeError(
                f"adapter_cls must be a BaseAdapter subclass, got {adapter_cls!r}"
            )
        if board_name in self._adapters:
            raise ValueError(
                f"Adapter already registered for board: {board_name}"
            )
        self._adapters[board_name] = adapter_cls
        logger.debug("Registered adapter for board %s: %s", board_name, adapter_cls.__name__)

    def unregister(self, board_name: str) -> bool:
        """
        Remove a board's adapter registration.

        Args:
            board_name: Board identifier to remove.

        Returns:
            True if a registration was removed, False if the board was unknown.
        """
        if board_name in self._adapters:
            del self._adapters[board_name]
            logger.debug("Unregistered adapter for board %s", board_name)
            return True
        return False

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, board_name: str) -> Type[BaseAdapter]:
        """
        Look up the registered adapter **class** for a board.

        Args:
            board_name: Board identifier.

        Returns:
            The adapter class registered for ``board_name``.

        Raises:
            KeyError: If no adapter is registered for ``board_name``.
        """
        try:
            return self._adapters[board_name]
        except KeyError:
            raise KeyError(
                f"No adapter registered for board: {board_name}"
            ) from None

    def create(
        self,
        board_name: str,
        config: dict,
        http_client=None,
    ) -> BaseAdapter:
        """
        Instantiate the adapter for a board.

        The adapter constructor is called as
        ``adapter_cls(config=config, http_client=http_client)`` — matching the
        shared ``BaseAdapter.__init__`` contract. No adapter constructor is
        changed.

        Args:
            board_name: Board identifier.
            config:     Full configuration dict passed to the adapter.
            http_client: Optional HTTP client forwarded to the adapter.

        Returns:
            A new adapter instance.

        Raises:
            KeyError: If no adapter is registered for ``board_name``.
        """
        adapter_cls = self.get(board_name)
        return adapter_cls(config=config, http_client=http_client)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_adapters(self) -> List[str]:
        """
        Return the sorted list of registered board names.
        """
        return sorted(self._adapters.keys())

    def is_registered(self, board_name: str) -> bool:
        """Return True if an adapter is registered for ``board_name``."""
        return board_name in self._adapters

    # ------------------------------------------------------------------
    # Enabled-boards resolution
    # ------------------------------------------------------------------

    @staticmethod
    def enabled_boards(
        config: Optional[dict],
        registered: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Determine which boards are enabled for a configuration.

        Reads the optional top-level ``boards`` section::

            boards:
                gseb:
                    enabled: true
                ncert:
                    enabled: false

        Rules:
            - Board-name matching is **case-insensitive** against the
              ``boards`` keys (which are lowercase by convention).
            - If the ``boards`` section is absent, every registered board is
              enabled (Phase 5 backward compatibility).
            - If ``boards`` is present but a specific board's entry is absent,
              that board defaults to **enabled**.
            - If a board's entry exists without an ``enabled`` key, it defaults
              to **enabled**.

        Args:
            config:     Full configuration dict (may be None or empty).
            registered: Optional list of registered board names to filter by.
                        If None, only boards present in ``boards`` are
                        considered.

        Returns:
            Sorted list of enabled board names (canonical case from
            ``registered`` when provided, else the ``boards`` keys upper-cased).
        """
        boards_section = (config or {}).get("boards") or {}

        if not boards_section:
            # No boards section → all registered boards enabled (Phase 5 mode).
            return sorted(registered) if registered is not None else []

        if registered is not None:
            enabled = [
                board for board in registered
                if AdapterRegistry._is_board_enabled(boards_section, board)
            ]
            return sorted(enabled)

        # No registered list supplied: derive from the boards section itself.
        enabled = [
            key.upper()
            for key, entry in boards_section.items()
            if AdapterRegistry._entry_enabled(entry)
        ]
        return sorted(enabled)

    @staticmethod
    def _is_board_enabled(boards_section: dict, board_name: str) -> bool:
        """Look up ``board_name`` (case-insensitively) in the boards section."""
        key = board_name.lower()
        entry = boards_section.get(key)
        if entry is None:
            # Try exact-case fallback, then default enabled.
            entry = boards_section.get(board_name)
        if entry is None:
            return True  # absent → enabled (backward compatibility)
        return AdapterRegistry._entry_enabled(entry)

    @staticmethod
    def _entry_enabled(entry) -> bool:
        """Resolve the enabled flag for a board's entry (dict or scalar)."""
        if isinstance(entry, dict):
            return bool(entry.get("enabled", True))
        # Scalar shorthand: ``gseb: true`` treated as enabled.
        if entry is None:
            return True
        return bool(entry)

    # ------------------------------------------------------------------
    # Dunder protocol (iteration / membership / size)
    # ------------------------------------------------------------------

    def __iter__(self):
        return iter(self.list_adapters())

    def __len__(self) -> int:
        return len(self._adapters)

    def __contains__(self, board_name: object) -> bool:
        return board_name in self._adapters

    def __repr__(self) -> str:
        return f"AdapterRegistry(boards={self.list_adapters()})"


# ---------------------------------------------------------------------------
# Default registry (lazy adapter imports to avoid circular dependencies)
# ---------------------------------------------------------------------------

def default_registry() -> AdapterRegistry:
    """
    Return a registry preloaded with the built-in adapters (GSEB, NCERT).

    Concrete adapter classes are imported **lazily inside this function** to
    avoid a circular import with :mod:`src.edf.adapters` (which re-exports
    them).

    Returns:
        A fresh :class:`AdapterRegistry` with GSEB and NCERT registered.
    """
    # Lazy imports: keeps this module free of any import-time dependency on
    # the concrete adapter modules (and therefore on utils.http, etc.).
    from src.edf.adapters.gseb import GSEBAdapter
    from src.edf.adapters.ncert import NCERTAdapter

    registry = AdapterRegistry()
    registry.register("GSEB", GSEBAdapter)
    registry.register("NCERT", NCERTAdapter)
    return registry
