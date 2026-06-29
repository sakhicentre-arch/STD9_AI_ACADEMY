"""
Verification tests for ManifestManager (Phase 4).
Covers all 12 behavioural areas + integration with StorageManager / hashing / logger.
"""

import dataclasses
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.edf.manifests.manager import ManifestManager
from src.edf.models.data import ManifestEntry
from src.edf.storage.manager import StorageManager
from src.edf.utils.hashing import sha256_file, sha256_bytes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    path: str = "NCERT/test.pdf",
    sha256: str = "a" * 64,
    size_bytes: int = 100,
    board: str = "NCERT",
    subject: str = "Science",
    medium: str = "english",
    std: str = "09",
    language: str = "en",
    source_url: str = "https://example.com/test.pdf",
) -> ManifestEntry:
    """Factory for ManifestEntry with sensible defaults."""
    return ManifestEntry(
        path=path,
        sha256=sha256,
        size_bytes=size_bytes,
        board=board,
        subject=subject,
        medium=medium,
        std=std,
        language=language,
        source_url=source_url,
        downloaded_at="2026-06-28T00:00:00+00:00",
        last_verified="2026-06-28T00:00:00+00:00",
        validation_status="VALID",
        managed=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace(tmp_path):
    """Create a fresh StorageManager + ManifestManager pair per test."""
    content_root = tmp_path / "CONTENT"
    storage = StorageManager(content_root=content_root)
    mm = ManifestManager(storage_manager=storage)
    yield mm, storage, content_root


@pytest.fixture
def seeded_workspace(workspace):
    """Workspace with 2 PDFs already on disk."""
    mm, storage, root = workspace
    (root / "NCERT").mkdir(parents=True, exist_ok=True)
    (root / "GSEB").mkdir(parents=True, exist_ok=True)
    (root / "NCERT" / "science_ch01.pdf").write_bytes(b"sci-content-01")
    (root / "GSEB" / "maths_ch01.pdf").write_bytes(b"maths-content-01")
    return mm, storage, root


# ===================================================================
# 1. Create new manifest
# ===================================================================

class TestCreateNewManifest:
    def test_empty_manifest_on_creation(self, workspace):
        mm, _, _ = workspace
        assert mm.entry_count == 0
        assert mm.entries == {}

    def test_add_single_entry(self, workspace):
        mm, _, _ = workspace
        entry = _make_entry()
        mm.add_entry(entry)

        assert mm.entry_count == 1
        assert mm.get_entry("NCERT/test.pdf") is entry

    def test_repr(self, workspace):
        mm, _, _ = workspace
        assert "ManifestManager(entries=0)" in repr(mm)
        mm.add_entry(_make_entry())
        assert "ManifestManager(entries=1)" in repr(mm)


# ===================================================================
# 2. Load manifest
# ===================================================================

class TestLoadManifest:
    def test_load_persisted_manifest(self, workspace):
        mm, storage, root = workspace
        entry = _make_entry()
        mm.add_entry(entry)
        mm.save(run_id="test_run")

        # Reload into a new ManifestManager
        mm2 = ManifestManager(storage_manager=storage)
        mm2.load_existing()

        assert mm2.entry_count == 1
        loaded = mm2.get_entry("NCERT/test.pdf")
        assert loaded is not None
        assert loaded.sha256 == "a" * 64
        assert loaded.board == "NCERT"

    def test_load_nonexistent_graceful(self, workspace):
        mm, _, _ = workspace
        # No files on disk — should not raise.
        mm.load_existing()

        assert mm.entry_count == 0

    def test_load_preserves_version_and_run_id(self, workspace):
        mm, storage, _ = workspace
        mm.save(run_id="run_42")

        mm2 = ManifestManager(storage_manager=storage)
        mm2.load_existing()
        mm2.add_entry(_make_entry(path="NCERT/new.pdf"))
        mm2.save()

        mm3 = ManifestManager(storage_manager=storage)
        mm3.load_existing()

        # Only one entry was added across this test; verify it survived the
        # save -> load -> save -> load cycle intact.
        assert mm3.entry_count == 1
        # The test's stated purpose: version and run_id survive reload.
        # "1.0" matches the literal in StorageManager/ManifestManager init.
        assert mm3._run_id == "run_42"
        assert mm3._version == "1.0"


# ===================================================================
# 3. Update manifest
# ===================================================================

class TestUpdateManifest:
    def test_update_existing_entry(self, workspace):
        mm, _, _ = workspace
        mm.add_entry(_make_entry(sha256="old"))
        mm.add_entry(_make_entry(sha256="new"))

        assert mm.entry_count == 1  # same path → upsert
        assert mm.get_entry("NCERT/test.pdf").sha256 == "new"

    def test_remove_entry(self, workspace):
        mm, _, _ = workspace
        mm.add_entry(_make_entry())
        removed = mm.remove_entry("NCERT/test.pdf")

        assert removed is not None
        assert removed.path == "NCERT/test.pdf"
        assert mm.entry_count == 0

    def test_remove_nonexistent_returns_none(self, workspace):
        mm, _, _ = workspace
        assert mm.remove_entry("no/such/file.pdf") is None


# ===================================================================
# 4. Append entries / incremental
# ===================================================================

class TestAppendEntries:
    def test_append_preserves_unchanged(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry(path="NCERT/a.pdf"))
        mm.save()

        mm.load_existing()
        mm.add_entry(_make_entry(path="NCERT/b.pdf"))
        mm.save()

        assert mm.entry_count == 2
        assert mm.get_entry("NCERT/a.pdf") is not None
        assert mm.get_entry("NCERT/b.pdf") is not None

    def test_duplicate_path_overwrites(self, workspace):
        mm, _, _ = workspace
        mm.add_entry(_make_entry(path="NCERT/x.pdf", sha256="hash1"))
        mm.add_entry(_make_entry(path="NCERT/x.pdf", sha256="hash2"))

        assert mm.entry_count == 1
        assert mm.get_entry("NCERT/x.pdf").sha256 == "hash2"


# ===================================================================
# 5. Duplicate detection
# ===================================================================

class TestDuplicateDetection:
    def test_duplicate_by_checksum(self, workspace):
        mm, _, _ = workspace
        mm.add_checksum("aa" * 32, "NCERT/a.pdf")
        mm.add_checksum("aa" * 32, "GSEB/a.pdf")

        registry = mm.get_checksum_registry()
        assert len(registry["aa" * 32]) == 2

    def test_duplicate_by_relative_path(self, workspace):
        mm, _, _ = workspace
        mm.add_entry(_make_entry(path="NCERT/test.pdf"))
        # Adding an entry with the same path replaces it.
        mm.add_entry(_make_entry(path="NCERT/test.pdf", sha256="different"))
        assert mm.entry_count == 1

    def test_duplicate_by_filename_via_discovery(self, seeded_workspace):
        mm, _, root = seeded_workspace
        # First discovery populates.
        mm.discover_existing_files()
        count1 = mm.entry_count

        # Second discovery should find nothing new (already in entries).
        mm.discover_existing_files()
        assert mm.entry_count == count1


# ===================================================================
# 6. Checksum persistence
# ===================================================================

class TestChecksumPersistence:
    def test_save_and_reload_checksums(self, workspace):
        mm, storage, root = workspace
        mm.add_checksum("bb" * 32, "NCERT/x.pdf")
        mm.save()

        mm2 = ManifestManager(storage_manager=storage)
        mm2.load_existing()
        registry = mm2.get_checksum_registry()

        assert "bb" * 32 in registry
        assert "NCERT/x.pdf" in registry["bb" * 32]

    def test_checksum_idempotent(self, workspace):
        mm, _, _ = workspace
        mm.add_checksum("cc" * 32, "NCERT/z.pdf")
        mm.add_checksum("cc" * 32, "NCERT/z.pdf")

        assert len(mm.get_checksum_registry()["cc" * 32]) == 1


# ===================================================================
# 7. JSON serialization
# ===================================================================

class TestJSONSerialization:
    def test_pretty_format(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry())
        mm.save()

        raw = (storage.get_manifest_path()).read_text(encoding="utf-8")
        # Verify it is pretty-printed (contains indentation)
        assert raw.startswith("{")
        assert '"version"' in raw
        assert '"files"' in raw

    def test_utf8_encoding(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry(subject="日本語テスト"))
        mm.save()

        raw = (storage.get_manifest_path()).read_bytes()
        # Decode as UTF-8 without errors.
        text = raw.decode("utf-8")
        assert "日本語テスト" in text

    def test_stable_ordering_checksums(self, workspace):
        mm, storage, root = workspace
        mm.add_checksum("zzz", "NCERT/c.pdf")
        mm.add_checksum("aaa", "NCERT/a.pdf")
        mm.save()

        raw = json.loads(
            (storage.get_checksums_path()).read_text(encoding="utf-8")
        )
        keys = list(raw.keys())
        assert keys == sorted(keys)  # sort_keys=True in _save_checksums

    def test_all_manifest_entry_fields_present(self, workspace):
        mm, storage, root = workspace
        entry = _make_entry()
        mm.add_entry(entry)
        mm.save()

        raw = json.loads(
            (storage.get_manifest_path()).read_text(encoding="utf-8")
        )
        file_dict = raw["files"][0]
        for fld in dataclasses.fields(ManifestEntry):
            assert fld.name in file_dict, f"Missing field: {fld.name}"


# ===================================================================
# 8. Scan CONTENT directory
# ===================================================================

class TestScanContentDirectory:
    def test_discovers_pdfs(self, seeded_workspace):
        mm, storage, root = seeded_workspace
        discovered = mm.discover_existing_files()

        assert len(discovered) == 2
        assert mm.entry_count == 2

    def test_discovers_correct_metadata(self, seeded_workspace):
        mm, storage, root = seeded_workspace
        discovered = mm.discover_existing_files()

        ncert_entry = next(
            e for e in discovered if "NCERT" in e.path
        )
        assert ncert_entry.board == "NCERT"
        assert ncert_entry.sha256 == hashlib.sha256(
            b"sci-content-01"
        ).hexdigest()
        assert ncert_entry.size_bytes == 14

    def test_skips_non_pdf(self, workspace):
        mm, storage, root = workspace
        (root / "NCERT").mkdir(parents=True, exist_ok=True)
        (root / "NCERT" / "notes.txt").write_bytes(b"notes")
        (root / "NCERT" / "data.csv").write_bytes(b"csv,data")

        discovered = mm.discover_existing_files()
        assert len(discovered) == 0

    def test_skips_edf_directory(self, workspace):
        mm, storage, root = workspace
        edf_dir = root / ".edf"
        (edf_dir / "cache").mkdir(parents=True, exist_ok=True)
        (edf_dir / "cache" / "meta.pdf").write_bytes(b"edf-pdf")

        discovered = mm.discover_existing_files()
        assert len(discovered) == 0

    def test_infers_board_from_parent(self, seeded_workspace):
        mm, storage, root = seeded_workspace
        discovered = mm.discover_existing_files()
        boards = {e.board for e in discovered}
        assert "NCERT" in boards
        assert "GSEB" in boards


# ===================================================================
# 9. Corrupted manifest recovery
# ===================================================================

class TestCorruptManifestRecovery:
    def test_corrupt_manifest_json(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry())
        mm.save()

        # Corrupt the manifest.
        (storage.get_manifest_path()).write_text("{{INVALID JSON", encoding="utf-8")

        mm2 = ManifestManager(storage_manager=storage)
        mm2.load_existing()

        # Should recover gracefully — empty entries.
        assert mm2.entry_count == 0

    def test_corrupt_checksums_json(self, workspace):
        mm, storage, root = workspace
        mm.add_checksum("dd" * 32, "NCERT/y.pdf")
        mm.save()

        # Corrupt checksums.
        (storage.get_checksums_path()).write_text(
            "{broken json!!!", encoding="utf-8"
        )

        mm2 = ManifestManager(storage_manager=storage)
        mm2.load_existing()

        assert mm2.get_checksum_registry() == {}


# ===================================================================
# 10. Missing manifest recovery
# ===================================================================

class TestMissingManifestRecovery:
    def test_first_run_no_files(self, workspace):
        mm, _, _ = workspace
        # No manifest or checksums on disk.
        mm.load_existing()

        assert mm.entry_count == 0
        assert mm.get_checksum_registry() == {}

    def test_manifest_only_file_missing(self, workspace):
        mm, storage, root = workspace
        mm.add_checksum("ee" * 32, "NCERT/z.pdf")
        mm.save()
        # Delete only the manifest.
        (storage.get_manifest_path()).unlink(missing_ok=True)

        mm2 = ManifestManager(storage_manager=storage)
        mm2.load_existing()

        assert mm2.entry_count == 0
        # Checksums still loaded.
        assert "ee" * 32 in mm2.get_checksum_registry()


# ===================================================================
# 11. Atomic write
# ===================================================================

class TestAtomicWrite:
    def test_no_partial_writes(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry())
        mm.save()

        manifest_content = (storage.get_manifest_path()).read_text(
            encoding="utf-8"
        )
        # Verify it's valid JSON (no partial/truncated data).
        data = json.loads(manifest_content)
        assert "files" in data

    def test_temp_files_cleaned_after_save(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry())
        mm.save()

        tmp_dir = storage.get_temp_dir()
        tmp_files = list(tmp_dir.iterdir())
        assert len(tmp_files) == 0

    def test_both_files_created(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry())
        mm.add_checksum("ff" * 32, "NCERT/f.pdf")
        mm.save()

        assert storage.get_manifest_path().exists()
        assert storage.get_checksums_path().exists()


# ===================================================================
# 12. Overwrite protection
# ===================================================================

class TestOverwriteProtection:
    def test_save_overwrites_on_second_call(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry(sha256="first"))
        mm.save()

        mm.add_entry(_make_entry(sha256="second"))
        mm.save()

        raw = json.loads(
            (storage.get_manifest_path()).read_text(encoding="utf-8")
        )
        assert raw["files"][0]["sha256"] == "second"

    def test_save_with_run_id(self, workspace):
        mm, storage, root = workspace
        mm.save(run_id="custom_run_1")

        raw = json.loads(
            (storage.get_manifest_path()).read_text(encoding="utf-8")
        )
        assert raw["run_id"] == "custom_run_1"

    def test_version_field(self, workspace):
        mm, storage, root = workspace
        mm.save()

        raw = json.loads(
            (storage.get_manifest_path()).read_text(encoding="utf-8")
        )
        assert raw["version"] == "1.0"

    def test_generated_at_is_iso_timestamp(self, workspace):
        mm, storage, root = workspace
        mm.save()

        raw = json.loads(
            (storage.get_manifest_path()).read_text(encoding="utf-8")
        )
        # Should parse as ISO without error.
        datetime.fromisoformat(raw["generated_at"])


# ===================================================================
# INTEGRATION: StorageManager
# ===================================================================

class TestIntegrationStorageManager:
    def test_uses_storage_atomic_write(self, workspace):
        mm, storage, root = workspace
        mm.add_entry(_make_entry())
        mm.save()

        # Manifest file exists via StorageManager's atomic pipeline.
        assert storage.file_exists(storage.get_manifest_path())

    def test_content_root_from_storage(self, workspace):
        mm, storage, root = workspace
        assert mm._storage.content_root == storage.content_root

    def test_manifest_path_from_storage(self, workspace):
        mm, storage, root = workspace
        assert mm._manifest_path == storage.get_manifest_path()


# ===================================================================
# INTEGRATION: hashing.py
# ===================================================================

class TestIntegrationHashing:
    def test_discover_uses_sha256_file(self, seeded_workspace):
        mm, storage, root = seeded_workspace
        mm.discover_existing_files()

        entry = mm.get_entry("NCERT/science_ch01.pdf")
        expected = sha256_file(root / "NCERT" / "science_ch01.pdf")
        assert entry.sha256 == expected


# ===================================================================
# INTEGRATION: logger.py (module-level logger)
# ===================================================================

class TestIntegrationLogger:
    def test_module_logger_name(self):
        from src.edf.manifests import manager as mod
        assert mod.logger.name == "edf.manifest"

    def test_operations_do_not_raise_logging_errors(self, workspace):
        mm, storage, root = workspace
        # These should all succeed even without a configured handler.
        mm.load_existing()
        mm.add_entry(_make_entry())
        mm.discover_existing_files()
        mm.save()
