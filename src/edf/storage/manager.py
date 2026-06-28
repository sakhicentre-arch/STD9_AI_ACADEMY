"""
EDF-L1 Storage Manager.

Manages all filesystem operations within the CONTENT directory:
- Path resolution for board/subject/medium combinations
- Duplicate detection via checksum registry
- Atomic file placement (temp → final)
- Directory structure creation and management
- Temp file lifecycle management
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set

from src.edf.utils.hashing import sha256_file


class StorageManager:
    """
    Manages the CONTENT filesystem and .edf metadata directory.

    Responsibilities:
        - Resolve target paths for downloaded files
        - Ensure directory structure exists
        - Detect existing files at target paths (duplicate detection)
        - Provide atomic file placement (write to temp, then rename)
        - Manage the checksums.json registry
        - Manage temp directory lifecycle

    Dependency Injection:
        Instantiated by the orchestrator with paths derived from ConfigLoader.
        No external dependencies beyond the filesystem.

    Example::

        storage = StorageManager(
            content_root=Path("./CONTENT"),
            edf_dir=".edf"
        )
        target = storage.resolve_path("GSEB", "09", "maths", "gujarati", "std09_gujarati_maths.pdf")
        exists = storage.file_exists(target)
        storage.ensure_dir(target)
    """

    def __init__(
        self,
        content_root: Path | str,
        edf_dir: str = ".edf",
    ) -> None:
        """
        Initialize the storage manager.

        Args:
            content_root: Absolute or relative path to the CONTENT directory.
            edf_dir: Name of the metadata subdirectory within content_root.
        """
        self._content_root = Path(content_root).resolve()
        self._edf_dir = edf_dir
        self._edf_path: Path = self._content_root / edf_dir
        # checksum registry: sha256 -> list of registered file paths (str)
        self._checksums: Dict[str, List[str]] = {}

        # Ensure the .edf directory structure exists on disk so that
        # metadata files and temp files can be written safely.
        self.ensure_edf_structure()
        # Load any existing checksum registry from disk to enable duplicate
        # detection across runs.
        self._load_checksums()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_checksums(self) -> None:
        """
        Load the checksum registry from .edf/checksums.json if it exists.

        On any read/parse error the registry is left empty (defensive
        default) and the corrupted file is NOT silently overwritten — the
        caller must explicitly save() to rewrite it.
        """
        path = self.get_checksums_path()
        if not path.exists() or not path.is_file():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # Validate shape: every value must be a list of strings.
                normalized: Dict[str, List[str]] = {}
                for key, paths in data.items():
                    if not isinstance(key, str):
                        continue
                    if isinstance(paths, str):
                        normalized[key] = [paths]
                    elif isinstance(paths, list):
                        normalized[key] = [str(p) for p in paths]
                self._checksums = normalized
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable registry — start empty. Existing on-disk
            # file is preserved until an explicit save() overwrites it.
            self._checksums = {}

    def _save_checksums(self) -> None:
        """
        Atomically persist the checksum registry to disk.

        Writes to a temp file in the same directory, fsyncs it, then renames
        over the final path.
        """
        self.ensure_dir(self.get_checksums_path())
        final_path = self.get_checksums_path()
        tmp_path = final_path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._checksums, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # os.replace is atomic on the same filesystem (POSIX + Windows).
        os.replace(str(tmp_path), str(final_path))

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def resolve_path(
        self,
        board: str,
        std: str,
        subject: str,
        medium: str,
        filename: str,
    ) -> Path:
        """
        Compute the canonical target path for a file.

        Directory structure: ``CONTENT/{board}/{filename}``

        Args:
            board: Board name (e.g., "GSEB").
            std: Standard/grade (unused in path, stored in manifest).
            subject: Subject name (unused in path, stored in manifest).
            medium: Instruction medium (unused in path, stored in manifest).
            filename: Target filename.

        Returns:
            Absolute Path to the target file location.
        """
        # Cross-platform path handling: Path() normalizes separators and
        # resolve() collapses any embedded traversal safely.
        safe_board = self._sanitize_segment(board)
        safe_filename = self._sanitize_segment(filename)
        return (self._content_root / safe_board / safe_filename).resolve()

    @staticmethod
    def _sanitize_segment(segment: str) -> str:
        """
        Strip path separators and parent-traversal tokens from a path segment.

        Ensures a malicious/erroneous board or filename cannot escape the
        CONTENT root via the resolved path.

        Args:
            segment: A single path component (board or filename).

        Returns:
            Sanitized segment safe to join into a path.
        """
        if segment is None:
            return ""
        # Replace OS-specific and alternate separators, then take basename.
        cleaned = str(segment).replace("\\", "/").split("/")[-1]
        # Collapse any remaining traversal fragments.
        parts = [p for p in cleaned.split("/") if p not in ("", ".", "..")]
        return parts[-1] if parts else ""

    def to_relative_path(self, absolute_path: Path | str) -> Optional[str]:
        """
        Convert an absolute path inside CONTENT to a relative POSIX string.

        Args:
            absolute_path: Absolute path within the CONTENT tree.

        Returns:
            POSIX-style relative path, or None if outside CONTENT.
        """
        try:
            rel = Path(absolute_path).resolve().relative_to(self._content_root)
        except (ValueError, OSError):
            return None
        return rel.as_posix()

    # ------------------------------------------------------------------
    # Directory management
    # ------------------------------------------------------------------

    def ensure_dir(self, path: Path | str) -> None:
        """
        Create parent directories if they don't exist.

        Args:
            path: Path whose parents should be created.
        """
        p = Path(path)
        target = p if p.is_dir() else p.parent
        target.mkdir(parents=True, exist_ok=True)

    def ensure_edf_structure(self) -> None:
        """
        Create the full .edf metadata directory structure.

        Creates: .edf/, .edf/logs/, .edf/tmp/, .edf/cache/
        """
        for subdir in ["logs", "tmp", "cache"]:
            (self._edf_path / subdir).mkdir(parents=True, exist_ok=True)
        # The .edf root itself is created by the loop above via parents=True.

    # ------------------------------------------------------------------
    # File existence and duplicate detection
    # ------------------------------------------------------------------

    def file_exists(self, path: Path | str) -> bool:
        """
        Check if a file exists at the given path.

        Args:
            path: File path to check.

        Returns:
            True if the file exists and is non-empty.
        """
        p = Path(path)
        try:
            return p.exists() and p.is_file() and p.stat().st_size > 0
        except OSError:
            return False

    def get_checksum(self, path: Path | str) -> Optional[str]:
        """
        Get the registered checksum for a file, if available.

        Args:
            path: File path to look up.

        Returns:
            SHA-256 hex string, or None if not registered.
        """
        # Normalize lookup to POSIX-style absolute path string for stability
        # across registry entries written by different code paths.
        key = str(Path(path).resolve())
        for sha, paths in self._checksums.items():
            if key in [str(Path(p).resolve()) for p in paths]:
                return sha
            if str(path) in paths:
                return sha
        return None

    def is_duplicate(self, sha256: str) -> Optional[List[str]]:
        """
        Check if a checksum already exists in the registry.

        Args:
            sha256: SHA-256 checksum to check.

        Returns:
            List of existing file paths with this checksum, or None.
        """
        return self._checksums.get(sha256) or None

    def register_checksum(self, sha256: str, path: Path | str) -> None:
        """
        Register a file path under its checksum and persist the registry.

        Args:
            sha256: SHA-256 hex digest.
            path: File path to register.
        """
        path_str = str(Path(path))
        if sha256 not in self._checksums:
            self._checksums[sha256] = []
        if path_str not in self._checksums[sha256]:
            self._checksums[sha256].append(path_str)
        self._save_checksums()

    def unregister_checksum(self, sha256: str, path: Path | str) -> None:
        """
        Remove a path from a checksum entry and persist the registry.

        Args:
            sha256: SHA-256 hex digest.
            path: File path to unregister.
        """
        if sha256 not in self._checksums:
            return
        path_str = str(path)
        if path_str in self._checksums[sha256]:
            self._checksums[sha256] = [
                p for p in self._checksums[sha256] if p != path_str
            ]
        if not self._checksums[sha256]:
            del self._checksums[sha256]
        self._save_checksums()

    # ------------------------------------------------------------------
    # File metadata generation
    # ------------------------------------------------------------------

    def get_file_metadata(self, path: Path | str) -> Dict[str, object]:
        """
        Generate structured metadata for a file on disk.

        Includes size, SHA-256, mtime, and absolute path. Used by the
        manifest layer to populate ManifestEntry fields.

        Args:
            path: Path to the file.

        Returns:
            Dict with keys: path, size_bytes, sha256, modified_at, exists.

        Raises:
            FileNotFoundError: If the file does not exist.
            OSError: If the file cannot be stat/read.
        """
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        stat = p.stat()
        return {
            "path": str(p.resolve()),
            "size_bytes": stat.st_size,
            "sha256": sha256_file(p),
            "modified_at": stat.st_mtime,
            "exists": True,
        }

    # ------------------------------------------------------------------
    # Atomic file placement
    # ------------------------------------------------------------------

    def atomic_place(
        self,
        temp_path: Path | str,
        target_path: Path | str,
        force: bool = False,
    ) -> Dict[str, object]:
        """
        Move a temp file to its final destination atomically.

        Performs the full safe-placement sequence:
          1. Validate the temp file exists and is non-empty.
          2. Ensure the target parent directory exists.
          3. If the target exists, honor duplicate detection:
             - force=False  -> refuse (return structured conflict result).
             - force=True   -> overwrite atomically.
          4. fsync the temp file, then os.replace() into place.
          5. Return a structured report.

        Args:
            temp_path: Path to the temporary file.
            target_path: Final destination path.
            force: If True, overwrite an existing target (--force semantics).

        Returns:
            Dict report with keys: placed (bool), target, sha256, size_bytes,
            conflict (bool), reason (Optional[str]).

        Raises:
            FileNotFoundError: If temp_path does not exist.
            OSError: If the move operation fails after best-effort cleanup.
        """
        tmp = Path(temp_path)
        target = Path(target_path)

        report: Dict[str, object] = {
            "placed": False,
            "target": str(target.resolve()),
            "sha256": None,
            "size_bytes": 0,
            "conflict": False,
            "reason": None,
        }

        if not self.file_exists(tmp):
            raise FileNotFoundError(f"Temp file does not exist or is empty: {tmp}")

        # Duplicate detection at the destination path.
        if self.file_exists(target) and not force:
            report["conflict"] = True
            report["reason"] = (
                f"Target already exists: {target}. Use force=True (--force) to overwrite."
            )
            # Clean up the orphaned temp file so the caller doesn't have to.
            self.cleanup_temp(tmp)
            return report

        # Ensure parent directory exists.
        self.ensure_dir(target)

        # fsync the temp file before rename for crash-safety.
        try:
            with open(tmp, "rb+") as f:
                os.fsync(f.fileno())
        except OSError:
            # fsync best-effort; rename can still proceed.
            pass

        try:
            os.replace(str(tmp), str(target))
        except OSError as exc:
            # Atomic rename failed — clean up temp and surface a structured error.
            self.cleanup_temp(tmp)
            report["reason"] = f"Atomic rename failed: {exc}"
            raise OSError(f"Atomic placement failed for {target}: {exc}") from exc

        # Populate report with the final file's metadata.
        try:
            meta = self.get_file_metadata(target)
            report["sha256"] = meta["sha256"]
            report["size_bytes"] = meta["size_bytes"]
        except OSError:
            # File is in place; metadata read is non-fatal.
            pass

        report["placed"] = True
        return report

    def atomic_write_bytes(
        self,
        target_path: Path | str,
        data: bytes,
        force: bool = False,
    ) -> Dict[str, object]:
        """
        Atomically write raw bytes to a target path.

        Convenience wrapper: writes to a temp file in the target's parent
        directory, fsyncs, then renames into place. Used for metadata files
        and small payloads.

        Args:
            target_path: Final destination path.
            data: Raw bytes to write.
            force: If True, overwrite an existing target.

        Returns:
            Dict report (same shape as atomic_place).
        """
        target = Path(target_path)
        self.ensure_dir(target)
        tmp_path = target.with_name(
            f".{target.name}.{uuid.uuid4().hex[:8]}.tmp"
        )
        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        return self.atomic_place(tmp_path, target, force=force)

    def create_temp_path(self, filename: str) -> Path:
        """
        Create a unique temp file path in the .edf/tmp/ directory.

        Args:
            filename: Base filename for the temp file.

        Returns:
            Path to the temp file (does not create the file).
        """
        safe_name = self._sanitize_segment(filename) or "download.bin"
        unique = uuid.uuid4().hex[:8]
        return self._edf_path / "tmp" / f"{unique}_{safe_name}"

    def cleanup_temp(self, path: Path | str) -> bool:
        """
        Safely remove a temp file. Used after failed downloads.

        Args:
            path: Temp file path to remove.

        Returns:
            True if a file was removed, False if it didn't exist.
        """
        p = Path(path)
        try:
            if p.exists() and p.is_file():
                p.unlink()
                return True
        except OSError:
            return False
        return False

    def cleanup_temp_dir(self) -> int:
        """
        Remove all files from the .edf/tmp/ directory.

        Returns:
            Number of files removed.
        """
        tmp_dir = self.get_temp_dir()
        removed = 0
        if not tmp_dir.exists():
            return 0
        for child in tmp_dir.iterdir():
            if child.is_file():
                try:
                    child.unlink()
                    removed += 1
                except OSError:
                    continue
        return removed

    # ------------------------------------------------------------------
    # Metadata paths
    # ------------------------------------------------------------------

    def get_checksums_path(self) -> Path:
        """Return path to .edf/checksums.json."""
        return self._edf_path / "checksums.json"

    def get_manifest_path(self) -> Path:
        """Return path to .edf/manifest.json."""
        return self._edf_path / "manifest.json"

    def get_log_dir(self) -> Path:
        """Return path to .edf/logs/."""
        return self._edf_path / "logs"

    def get_temp_dir(self) -> Path:
        """Return path to .edf/tmp/."""
        return self._edf_path / "tmp"

    def get_cache_dir(self) -> Path:
        """Return path to .edf/cache/."""
        return self._edf_path / "cache"

    @property
    def content_root(self) -> Path:
        """Return the content root directory."""
        return self._content_root

    @property
    def edf_path(self) -> Path:
        """Return the .edf metadata directory path."""
        return self._edf_path

    @property
    def checksums(self) -> Dict[str, List[str]]:
        """Return the in-memory checksum registry."""
        return self._checksums

    def __repr__(self) -> str:
        return f"StorageManager(content_root={self._content_root!s})"
