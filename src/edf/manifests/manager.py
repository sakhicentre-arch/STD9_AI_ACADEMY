"""
EDF-L1 Manifest Manager.

Generates and maintains manifest.json and checksums.json for the
CONTENT repository. Supports incremental updates and atomic writes.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.edf.models.data import ManifestEntry
from src.edf.utils.hashing import sha256_file

logger = logging.getLogger("edf.manifest")


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
        Handles corrupt or malformed files gracefully without data loss.
        """
        # --- Load manifest.json ---
        if self._manifest_path.exists() and self._manifest_path.is_file():
            try:
                with open(self._manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for entry_data in data.get("files", []):
                        if not isinstance(entry_data, dict):
                            logger.warning("Skipping non-dict manifest entry")
                            continue
                        try:
                            entry = ManifestEntry(**entry_data)
                            self._entries[entry.path] = entry
                        except TypeError:
                            logger.warning(
                                "Skipping malformed manifest entry: %s",
                                entry_data,
                            )
                    self._version = data.get("version", self._version)
                    self._run_id = data.get("run_id", self._run_id)
                    logger.info(
                        "Loaded manifest: %d entries (run_id=%s)",
                        len(self._entries),
                        self._run_id,
                    )
                else:
                    logger.warning("Manifest root is not a dict; starting empty.")
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Failed to load manifest.json (%s); starting empty.", exc
                )
                # Leave entries empty — corrupted file is NOT overwritten.

        # --- Load checksums.json ---
        if self._checksums_path.exists() and self._checksums_path.is_file():
            try:
                with open(self._checksums_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for key, paths in data.items():
                        if not isinstance(key, str):
                            continue
                        if isinstance(paths, str):
                            self._checksums[key] = [paths]
                        elif isinstance(paths, list):
                            self._checksums[key] = [str(p) for p in paths]
                    logger.info(
                        "Loaded checksums: %d unique hashes",
                        len(self._checksums),
                    )
                else:
                    logger.warning("Checksums root is not a dict; starting empty.")
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Failed to load checksums.json (%s); starting empty.", exc
                )

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

        Walks the content root recursively, discovers .pdf files,
        computes SHA-256 checksums, and infers metadata from the
        directory structure. Skips files under the .edf metadata directory.

        Used on first run to inventory the existing repository.

        Returns:
            List of ManifestEntry objects for discovered files.
        """
        discovered: List[ManifestEntry] = []
        content_root = self._storage.content_root
        edf_path = self._storage.edf_path

        try:
            pdf_files = list(content_root.rglob("*.pdf"))
        except OSError as exc:
            logger.warning("Filesystem scan failed: %s", exc)
            return discovered

        for pdf_path in pdf_files:
            # Skip files inside the .edf metadata directory.
            try:
                pdf_path.resolve().relative_to(edf_path.resolve())
                continue
            except ValueError:
                pass  # Not under .edf — process it.

            # Compute relative path from content root.
            rel = self._storage.to_relative_path(pdf_path)
            if rel is None:
                logger.warning("File outside content root: %s", pdf_path)
                continue

            # Skip files already in the manifest (avoid duplicates).
            if rel in self._entries:
                continue

            # Infer metadata from the directory structure.
            parts = Path(rel).parts
            board = parts[0] if len(parts) > 1 else ""
            subject = parts[1] if len(parts) > 2 else ""
            filename = pdf_path.name

            # Compute SHA-256 and file size.
            try:
                sha = sha256_file(pdf_path)
                size = pdf_path.stat().st_size
            except OSError as exc:
                logger.warning("Cannot read %s: %s", pdf_path, exc)
                continue

            entry = ManifestEntry(
                path=rel,
                sha256=sha,
                size_bytes=size,
                board=board,
                subject=subject,
                medium="",
                std="",
                language="",
                managed=True,
            )
            self._entries[rel] = entry
            self.add_checksum(sha, rel)
            discovered.append(entry)

        logger.info(
            "Discovered %d new PDF files (total managed: %d)",
            len(discovered),
            self.entry_count,
        )
        return discovered

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
        if run_id is not None:
            self._run_id = run_id
        self._save_manifest(run_id)
        self._save_checksums()
        logger.info(
            "Manifest saved: %d entries, %d checksums (run_id=%s)",
            self.entry_count,
            len(self._checksums),
            self._run_id,
        )

    def _save_manifest(self, run_id: Optional[str] = None) -> None:
        """
        Write manifest.json atomically.

        Uses StorageManager.atomic_write_bytes for crash-safe placement.

        Args:
            run_id: Run identifier for the manifest header.
        """
        manifest = {
            "version": self._version,
            "run_id": run_id or self._run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files": [dataclasses.asdict(e) for e in self._entries.values()],
        }
        data = json.dumps(
            manifest, indent=2, ensure_ascii=False, sort_keys=False
        ).encode("utf-8")
        self._storage.atomic_write_bytes(self._manifest_path, data, force=True)

    def _save_checksums(self) -> None:
        """Write checksums.json atomically."""
        data = json.dumps(
            self._checksums, indent=2, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        self._storage.atomic_write_bytes(self._checksums_path, data, force=True)

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
