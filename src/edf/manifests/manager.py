"""
EDF-L1 Manifest Manager.

Generates and maintains manifest.json and checksums.json for the
CONTENT repository. Supports incremental updates and atomic writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.edf.models.data import ManifestEntry


class ManifestManager:
    """
    Manages the CONTENT repository manifest and checksum registry.

    Responsibilities:
        - Generate manifest.json with full file inventory
        - Generate and maintain checksums.json (SHA-256 registry)
        - Support incremental merges (new files added without rebuilding)
        - Atomic writes (write to temp, rename to final)
        - Load existing manifests for duplicate detection

    Dependency Injection:
        Instantiated by the orchestrator with a StorageManager reference.

    Example::

        manifest_mgr = ManifestManager(storage_manager)
        manifest_mgr.load_existing()
        manifest_mgr.add_entry(entry)
        manifest_mgr.add_checksum(sha256, filepath)
        manifest_mgr.save()
    """

    def __init__(self, storage_manager) -> None:
        """
        Initialize the manifest manager.

        Args:
            storage_manager: StorageManager instance for path resolution.
        """
        self._storage = storage_manager
        self._manifest_path: Path = storage_manager.get_manifest_path()
        self._checksums_path: Path = storage_manager.get_checksums_path()
        self._entries: Dict[str, ManifestEntry] = {}
        self._checksums: Dict[str, List[str]] = {}
        self._run_id: str = ""
        self._version: str = "1.0"

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_existing(self) -> None:
        """
        Load existing manifest.json and checksums.json from disk.

        Creates empty structures if files don't exist (first run).
        """
        # TODO: Implement manifest.json loading.
        # if self._manifest_path.exists():
        #     with open(self._manifest_path, "r", encoding="utf-8") as f:
        #         data = json.load(f)
        #     for entry_data in data.get("files", []):
        #         entry = ManifestEntry(**entry_data)
        #         self._entries[entry.path] = entry

        # TODO: Implement checksums.json loading.
        # if self._checksums_path.exists():
        #     with open(self._checksums_path, "r", encoding="utf-8") as f:
        #         self._checksums = json.load(f)
        pass

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_entry(self, entry: ManifestEntry) -> None:
        """
        Add or update a single manifest entry.

        Args:
            entry: The ManifestEntry to register.
        """
        self._entries[entry.path] = entry

    def add_checksum(self, sha256: str, filepath: str) -> None:
        """
        Register a checksum in the registry.

        Args:
            sha256: SHA-256 hex digest.
            filepath: Relative path from content root.
        """
        if sha256 not in self._checksums:
            self._checksums[sha256] = []
        if filepath not in self._checksums[sha256]:
            self._checksums[sha256].append(filepath)

    def remove_entry(self, path: str) -> Optional[ManifestEntry]:
        """
        Remove a manifest entry by path.

        Args:
            path: Relative file path to remove.

        Returns:
            The removed entry, or None if not found.
        """
        return self._entries.pop(path, None)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_existing_files(self) -> List[ManifestEntry]:
        """
        Scan CONTENT/ for existing PDF files and build initial entries.

        Used on first run to inventory the existing repository.

        Returns:
            List of ManifestEntry objects for discovered files.
        """
        # TODO: Implement filesystem scan.
        # - Walk CONTENT/ recursively
        # - Filter for .pdf files
        # - Compute SHA-256 for each
        # - Infer board from parent directory
        # - Build ManifestEntry for each file
        return []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, run_id: Optional[str] = None) -> None:
        """
        Save manifest.json and checksums.json atomically.

        Writes to temp files first, then renames to final paths.

        Args:
            run_id: Optional run identifier to embed in the manifest.
        """
        # TODO: Implement atomic save.
        # self._save_manifest(run_id)
        # self._save_checksums()
        pass

    def _save_manifest(self, run_id: Optional[str] = None) -> None:
        """
        Write manifest.json atomically.

        Args:
            run_id: Run identifier for the manifest header.
        """
        # TODO: Build manifest dict, write to temp, rename.
        pass

    def _save_checksums(self) -> None:
        """Write checksums.json atomically."""
        # TODO: Write checksums dict to temp, rename.
        pass

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_entry(self, path: str) -> Optional[ManifestEntry]:
        """
        Look up a manifest entry by file path.

        Args:
            path: Relative file path.

        Returns:
            ManifestEntry or None.
        """
        return self._entries.get(path)

    def get_checksum_registry(self) -> Dict[str, List[str]]:
        """Return the full checksum registry."""
        return self._checksums

    @property
    def entries(self) -> Dict[str, ManifestEntry]:
        """Return all manifest entries keyed by path."""
        return self._entries

    @property
    def entry_count(self) -> int:
        """Return the number of managed files."""
        return len(self._entries)

    def __repr__(self) -> str:
        return f"ManifestManager(entries={self.entry_count})"
