"""
Verification tests for StorageManager.
Covers all 12 behavioural areas required by the verification spec.
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

import pytest

from src.edf.storage.manager import StorageManager
from src.edf.utils.hashing import sha256_file, sha256_bytes


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace(tmp_path):
    """Create a fresh temporary workspace for each test."""
    content_root = tmp_path / "CONTENT"
    storage = StorageManager(content_root=content_root)
    yield storage, content_root


# ===================================================================
# 1. ensure_dir
# ===================================================================

class TestEnsureDir:
    def test_creates_missing_parent_directories(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "deep" / "nested" / "file.pdf"
        assert not target.parent.exists()

        storage.ensure_dir(target)

        assert target.parent.is_dir()

    def test_idempotent_on_existing_directory(self, workspace):
        storage, root = workspace
        target = root / "GSEB"
        storage.ensure_dir(target)
        # Calling ensure_dir with a file path whose parent already exists
        # must not raise.
        storage.ensure_dir(target / "subfile.txt")

        assert target.is_dir()

    def test_directory_path_as_input(self, workspace):
        storage, root = workspace
        # Calling ensure_dir with a directory path creates it.
        dir_path = root / "some_dir"
        storage.ensure_dir(dir_path / "child.txt")
        # The parent 'some_dir' should exist as a side-effect.
        assert dir_path.is_dir()


# ===================================================================
# 2. atomic_write_bytes
# ===================================================================

class TestAtomicWriteBytes:
    def test_writes_data_and_creates_file(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "test.txt"
        data = b"hello world"

        report = storage.atomic_write_bytes(target, data)

        assert report["placed"] is True
        assert target.exists()
        assert target.read_bytes() == data

    def test_sha256_in_report(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "test.bin"
        data = os.urandom(64)
        expected_sha = sha256_bytes(data)

        report = storage.atomic_write_bytes(target, data)

        assert report["sha256"] == expected_sha

    def test_size_bytes_in_report(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "test.bin"
        data = b"x" * 1234

        report = storage.atomic_write_bytes(target, data)

        assert report["size_bytes"] == 1234

    def test_target_in_report_is_absolute(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "test.txt"

        report = storage.atomic_write_bytes(target, b"data")

        assert report["target"] == str(target.resolve())


# ===================================================================
# 3. atomic_place
# ===================================================================

class TestAtomicPlace:
    def test_places_temp_file_to_target(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "placed.pdf"
        tmp = root / ".edf" / "tmp" / "source.tmp"
        tmp.write_bytes(b"placed-content")

        report = storage.atomic_place(tmp, target)

        assert report["placed"] is True
        assert target.exists()
        assert target.read_bytes() == b"placed-content"
        assert not tmp.exists()  # temp file consumed by rename

    def test_removes_temp_on_conflict_force_false(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "existing.pdf"
        storage.ensure_dir(target)
        target.write_bytes(b"original")
        tmp = root / ".edf" / "tmp" / "new.tmp"
        tmp.write_bytes(b"new-content")

        report = storage.atomic_place(tmp, target, force=False)

        assert report["placed"] is False
        assert report["conflict"] is True
        assert "force=True" in report["reason"]
        assert target.read_bytes() == b"original"
        assert not tmp.exists()  # temp cleaned up

    def test_raises_on_missing_temp(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "missing.pdf"

        with pytest.raises(FileNotFoundError, match="Temp file does not exist"):
            storage.atomic_place(root / "nonexistent.tmp", target)


# ===================================================================
# 4. cleanup_temp
# ===================================================================

class TestCleanupTemp:
    def test_removes_existing_temp_file(self, workspace):
        storage, root = workspace
        tmp = root / ".edf" / "tmp" / "to_delete.tmp"
        tmp.write_bytes(b"junk")

        result = storage.cleanup_temp(tmp)

        assert result is True
        assert not tmp.exists()

    def test_returns_false_for_missing_file(self, workspace):
        storage, root = workspace

        result = storage.cleanup_temp(root / ".edf" / "tmp" / "ghost.tmp")

        assert result is False


# ===================================================================
# 5. duplicate detection
# ===================================================================

class TestDuplicateDetection:
    def test_is_duplicate_returns_none_for_unknown(self, workspace):
        storage, _ = workspace

        assert storage.is_duplicate("aa" * 32) is None

    def test_register_and_detect(self, workspace):
        storage, root = workspace
        sha = "a" * 64
        path = str(root / "GSEB" / "file.pdf")
        storage.register_checksum(sha, path)

        result = storage.is_duplicate(sha)

        assert result is not None
        assert path in result

    def test_get_checksum_returns_registered_value(self, workspace):
        storage, root = workspace
        sha = "b" * 64
        path = str(root / "GSEB" / "file.pdf")
        storage.register_checksum(sha, path)

        assert storage.get_checksum(path) == sha

    def test_unregister_checksum(self, workspace):
        storage, root = workspace
        sha = "c" * 64
        path = str(root / "GSEB" / "file.pdf")
        storage.register_checksum(sha, path)
        storage.unregister_checksum(sha, path)

        assert storage.is_duplicate(sha) is None

    def test_checksum_persists_across_reload(self, workspace):
        storage, root = workspace
        sha = "d" * 64
        path = str(root / "GSEB" / "file.pdf")
        storage.register_checksum(sha, path)

        # Re-instantiate to reload from disk
        storage2 = StorageManager(content_root=root)

        assert storage2.is_duplicate(sha) is not None
        assert path in storage2.is_duplicate(sha)

    def test_register_duplicate_path_idempotent(self, workspace):
        storage, root = workspace
        sha = "e" * 64
        path = str(root / "GSEB" / "file.pdf")
        storage.register_checksum(sha, path)
        storage.register_checksum(sha, path)

        assert len(storage.is_duplicate(sha)) == 1


# ===================================================================
# 6. overwrite force=True
# ===================================================================

class TestOverwriteForceTrue:
    def test_overwrites_existing_file(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "overwrite.pdf"
        storage.ensure_dir(target)
        target.write_bytes(b"old-content")

        tmp = root / ".edf" / "tmp" / "replacement.tmp"
        tmp.write_bytes(b"new-content")

        report = storage.atomic_place(tmp, target, force=True)

        assert report["placed"] is True
        assert target.read_bytes() == b"new-content"
        assert not tmp.exists()

    def test_atomic_write_bytes_overwrites_with_force(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "meta.json"
        storage.atomic_write_bytes(target, b"v1")

        report = storage.atomic_write_bytes(target, b"v2", force=True)

        assert report["placed"] is True
        assert target.read_bytes() == b"v2"


# ===================================================================
# 7. overwrite force=False (refused)
# ===================================================================

class TestOverwriteForceFalse:
    def test_refuses_overwrite(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "protected.pdf"
        storage.atomic_write_bytes(target, b"original")

        tmp = root / ".edf" / "tmp" / "conflict.tmp"
        tmp.write_bytes(b"new")

        report = storage.atomic_place(tmp, target, force=False)

        assert report["placed"] is False
        assert report["conflict"] is True
        assert target.read_bytes() == b"original"

    def test_atomic_write_bytes_refuses_with_force_false(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "protected.json"
        storage.atomic_write_bytes(target, b"original")

        report = storage.atomic_write_bytes(target, b"new", force=False)

        assert report["placed"] is False
        assert report["conflict"] is True


# ===================================================================
# 8. metadata generation
# ===================================================================

class TestMetadataGeneration:
    def test_metadata_fields(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "meta_test.pdf"
        data = b"x" * 500
        storage.atomic_write_bytes(target, data)

        meta = storage.get_file_metadata(target)

        assert "path" in meta
        assert "size_bytes" in meta
        assert "sha256" in meta
        assert "modified_at" in meta
        assert "exists" in meta
        assert meta["exists"] is True
        assert meta["size_bytes"] == 500
        assert meta["sha256"] == sha256_bytes(data)

    def test_metadata_raises_for_missing_file(self, workspace):
        storage, root = workspace

        with pytest.raises(FileNotFoundError):
            storage.get_file_metadata(root / "GSEB" / "nonexistent.pdf")


# ===================================================================
# 9. SHA-256 integration
# ===================================================================

class TestSHA256Integration:
    def test_sha256_consistency_across_methods(self, workspace):
        storage, root = workspace
        data = b"test-content-for-sha256"
        target = root / "GSEB" / "sha_test.bin"
        expected = hashlib.sha256(data).hexdigest()

        report = storage.atomic_write_bytes(target, data)
        meta = storage.get_file_metadata(target)
        direct = sha256_file(target)

        assert report["sha256"] == expected
        assert meta["sha256"] == expected
        assert direct == expected

    def test_checksum_registry_stores_sha256(self, workspace):
        storage, root = workspace
        data = b"register-me"
        target = root / "GSEB" / "registered.pdf"
        report = storage.atomic_write_bytes(target, data)

        storage.register_checksum(report["sha256"], target)
        lookup = storage.get_checksum(target)

        assert lookup == report["sha256"]


# ===================================================================
# 10. temporary file cleanup after failures
# ===================================================================

class TestTempCleanupAfterFailure:
    def test_temp_removed_on_rename_failure(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "fail.pdf"
        tmp = root / ".edf" / "tmp" / "bad.tmp"
        tmp.write_bytes(b"data")

        # Point target at a directory to force rename failure
        target.mkdir(parents=True, exist_ok=True)

        with pytest.raises(OSError, match="Atomic placement failed"):
            storage.atomic_place(tmp, target)

        # Temp should be cleaned up
        assert not tmp.exists()

    def test_conflict_cleans_temp(self, workspace):
        storage, root = workspace
        target = root / "GSEB" / "taken.pdf"
        storage.atomic_write_bytes(target, b"taken")

        tmp = root / ".edf" / "tmp" / "orphan.tmp"
        tmp.write_bytes(b"orphan-data")

        report = storage.atomic_place(tmp, target, force=False)

        assert not tmp.exists()

    def test_cleanup_temp_dir_clears_all(self, workspace):
        storage, root = workspace
        tmp_dir = storage.get_temp_dir()
        for i in range(5):
            (tmp_dir / f"junk_{i}.tmp").write_bytes(b"x")

        removed = storage.cleanup_temp_dir()

        assert removed == 5
        assert not any(tmp_dir.iterdir())


# ===================================================================
# 11. Windows path handling
# ===================================================================

class TestWindowsPathHandling:
    def test_resolve_path_produces_absolute(self, workspace):
        storage, root = workspace
        result = storage.resolve_path("GSEB", "09", "maths", "gujarati", "test.pdf")

        assert result.is_absolute()

    def test_to_relative_path(self, workspace):
        storage, root = workspace
        abs_path = root / "GSEB" / "file.pdf"

        rel = storage.to_relative_path(abs_path)

        assert rel == "GSEB/file.pdf"

    def test_to_relative_path_outside_content_returns_none(self, workspace):
        storage, _ = workspace

        result = storage.to_relative_path("C:\\Windows\\System32\\config")

        assert result is None

    def test_sanitize_blocks_traversal(self, workspace):
        storage, _ = workspace
        safe = storage._sanitize_segment("../../../etc/passwd")

        assert "../" not in safe
        assert ".." not in safe

    def test_sanitize_strips_backslashes(self, workspace):
        storage, _ = workspace
        safe = storage._sanitize_segment("foo\\bar\\baz")

        assert "\\" not in safe
        assert safe == "baz"

    def test_sanitize_none_returns_empty(self, workspace):
        storage, _ = workspace

        assert storage._sanitize_segment(None) == ""

    def test_path_with_mixed_separators(self, workspace):
        storage, root = workspace
        result = storage.resolve_path("GSEB", "09", "maths", "gu", "my/file.pdf")

        assert "my" not in str(result).replace(os.sep, "/").split("/")[-1] or result.name == "file.pdf"


# ===================================================================
# 12. edf structure and checksums persistence
# ===================================================================

class TestEDFStructure:
    def test_edf_dirs_created(self, workspace):
        storage, root = workspace
        edf = root / ".edf"

        assert (edf / "logs").is_dir()
        assert (edf / "tmp").is_dir()
        assert (edf / "cache").is_dir()

    def test_checksums_path(self, workspace):
        storage, root = workspace

        assert "checksums.json" in str(storage.get_checksums_path())

    def test_corrupt_checksums_handled_gracefully(self, workspace):
        storage, root = workspace
        ck_path = storage.get_checksums_path()
        ck_path.write_text("{{invalid json")

        storage2 = StorageManager(content_root=root)

        assert storage2.checksums == {}

    def test_checksums_with_string_value_normalized(self, workspace):
        storage, root = workspace
        ck_path = storage.get_checksums_path()
        ck_path.write_text('{"abc123": "path/to/file.pdf"}')

        storage2 = StorageManager(content_root=root)

        assert storage2.checksums["abc123"] == ["path/to/file.pdf"]

    def test_create_temp_path_uniqueness(self, workspace):
        storage, _ = workspace

        p1 = storage.create_temp_path("test.pdf")
        p2 = storage.create_temp_path("test.pdf")

        assert p1 != p2
        assert p1.parent == storage.get_temp_dir()

    def test_repr(self, workspace):
        storage, _ = workspace

        assert "StorageManager" in repr(storage)

    def test_properties(self, workspace):
        storage, root = workspace

        assert storage.content_root == root.resolve()
        assert storage.edf_path == (root / ".edf").resolve()
        assert isinstance(storage.checksums, dict)
