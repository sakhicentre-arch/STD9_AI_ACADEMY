"""
Tests for the EDF-L1 ConfigLoader (src/edf/core/config.py).

These tests exercise:
  - Successful loading of a well-formed config.yaml
  - Sensible defaults applied for optional keys
  - Validation rules V1–V10 (required fields, types, ranges, templates)
  - Alias canonicalisation (chunk_size_bytes → chunk_size)
  - Typed accessor properties
  - get_textbooks(board) lookup

Each test writes a small YAML to a temp file and constructs a ConfigLoader
against it, so no on-disk fixtures are required.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from src.edf.core.config import ConfigLoader, ConfigValidationError


# ---------------------------------------------------------------------------
# Minimal valid config used as a starting point by most tests.
# ---------------------------------------------------------------------------
MINIMAL_VALID_YAML = textwrap.dedent(
    """\
    version: "1.0"
    general:
      content_root: ./CONTENT
    """
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def write_config(tmp_path: Path, content: str) -> Path:
    """Write ``content`` to a config file in ``tmp_path`` and return its path."""
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def load(tmp_path: Path, content: str = MINIMAL_VALID_YAML) -> ConfigLoader:
    """Convenience: write then load a ConfigLoader, returning the instance."""
    return ConfigLoader(write_config(tmp_path, content))


# ---------------------------------------------------------------------------
# Construction / file loading
# ---------------------------------------------------------------------------
class TestLoading:
    def test_missing_file_raises_filenotfound(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ConfigLoader(tmp_path / "does_not_exist.yaml")

    def test_malformed_yaml_raises_validation_error(self, tmp_path):
        # Unclosed quote / bad indentation makes invalid YAML.
        path = write_config(tmp_path, "version: '1.0\n  general: [unterminated")
        with pytest.raises(ConfigValidationError):
            ConfigLoader(path)

    def test_root_not_mapping_raises(self, tmp_path):
        path = write_config(tmp_path, "- just\n- a\n- list\n")
        with pytest.raises(ConfigValidationError):
            ConfigLoader(path)

    def test_empty_file_loads_with_defaults(self, tmp_path):
        # An empty file → None → treated as {} → version missing → V1 fails.
        path = write_config(tmp_path, "")
        with pytest.raises(ConfigValidationError):
            ConfigLoader(path)


# ---------------------------------------------------------------------------
# Version validation (V1)
# ---------------------------------------------------------------------------
class TestVersionValidation:
    def test_missing_version_raises(self, tmp_path):
        content = "general:\n  content_root: ./CONTENT\n"
        with pytest.raises(ConfigValidationError, match="version"):
            load(tmp_path, content)

    def test_wrong_version_raises(self, tmp_path):
        content = 'version: "2.0"\ngeneral:\n  content_root: ./CONTENT\n'
        with pytest.raises(ConfigValidationError, match="version"):
            load(tmp_path, content)

    def test_version_must_be_string_one_dot_zero(self, tmp_path):
        # version: 1.0 (float) is NOT accepted — must be the string "1.0".
        content = "version: 1.0\ngeneral:\n  content_root: ./CONTENT\n"
        with pytest.raises(ConfigValidationError, match="version"):
            load(tmp_path, content)

    def test_version_property_returns_string(self, tmp_path):
        loader = load(tmp_path)
        assert loader.version == "1.0"


# ---------------------------------------------------------------------------
# general section (V2, V3)
# ---------------------------------------------------------------------------
class TestGeneralSection:
    def test_general_not_mapping_raises(self, tmp_path):
        content = 'version: "1.0"\ngeneral: not-a-mapping\n'
        with pytest.raises(ConfigValidationError, match="general"):
            load(tmp_path, content)

    def test_content_root_must_be_nonempty_string(self, tmp_path):
        for bad in ("", "   "):
            content = (
                'version: "1.0"\n'
                f"general:\n  content_root: '{bad}'\n"
            )
            with pytest.raises(ConfigValidationError, match="content_root"):
                load(tmp_path, content)

    def test_missing_content_root_uses_default(self, tmp_path):
        # No general.content_root → default applied in _apply_defaults, so V3
        # passes with the default value.
        content = 'version: "1.0"\ngeneral: {}\n'
        loader = load(tmp_path, content)
        assert loader.content_root == Path(ConfigLoader.DEFAULT_CONTENT_ROOT)

    def test_dry_run_defaults_to_false(self, tmp_path):
        loader = load(tmp_path)
        assert loader.is_dry_run is False

    def test_force_overwrite_defaults_to_false(self, tmp_path):
        loader = load(tmp_path)
        assert loader.is_force_overwrite is False

    def test_dry_run_true_is_preserved(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n  dry_run: true\n"
        )
        loader = load(tmp_path, content)
        assert loader.is_dry_run is True

    def test_no_general_section_uses_defaults(self, tmp_path):
        """Regression: omitting the 'general' key entirely must not raise
        AttributeError — defaults should be injected silently."""
        content = 'version: "1.0"\n'
        loader = load(tmp_path, content)
        assert loader.content_root == Path(ConfigLoader.DEFAULT_CONTENT_ROOT)

    def test_edf_metadata_dir_default(self, tmp_path):
        loader = load(tmp_path)
        assert loader.edf_metadata_dir == ConfigLoader.DEFAULT_EDF_METADATA_DIR


# ---------------------------------------------------------------------------
# download section (V4) — numeric type/range checks
# ---------------------------------------------------------------------------
class TestDownloadValidation:
    def _with_download(self, tmp_path, download_yaml):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            f"download:\n{download_yaml}\n"
        )
        return load(tmp_path, content)

    @pytest.mark.parametrize(
        "key",
        ["max_retries", "timeout_seconds", "backoff_base_seconds", "delay_seconds"],
    )
    def test_negative_numeric_raises(self, tmp_path, key):
        with pytest.raises(ConfigValidationError, match=key):
            self._with_download(tmp_path, f"  {key}: -1")

    @pytest.mark.parametrize(
        "key",
        ["max_retries", "timeout_seconds", "backoff_base_seconds"],
    )
    def test_non_integer_numeric_raises(self, tmp_path, key):
        with pytest.raises(ConfigValidationError, match=key):
            self._with_download(tmp_path, f"  {key}: 1.5")

    def test_delay_seconds_accepts_float(self, tmp_path):
        """delay_seconds is the exception: sub-second delays require float."""
        loader = self._with_download(tmp_path, "  delay_seconds: 0.5")
        assert loader.download["delay_seconds"] == 0.5

    def test_download_not_mapping_raises(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "download: not-a-mapping\n"
        )
        with pytest.raises(ConfigValidationError, match="download"):
            load(tmp_path, content)

    def test_download_defaults_applied(self, tmp_path):
        loader = load(tmp_path)
        dl = loader.download
        assert dl["max_retries"] == ConfigLoader.DEFAULT_MAX_RETRIES
        assert dl["timeout_seconds"] == ConfigLoader.DEFAULT_TIMEOUT_SECONDS
        assert dl["backoff_base_seconds"] == ConfigLoader.DEFAULT_BACKOFF_BASE_SECONDS
        assert dl["delay_seconds"] == ConfigLoader.DEFAULT_DELAY_SECONDS
        assert dl["user_agent"] == ConfigLoader.DEFAULT_USER_AGENT
        assert dl["temp_dir"] == ConfigLoader.DEFAULT_TEMP_DIR


# ---------------------------------------------------------------------------
# validation section (V5)
# ---------------------------------------------------------------------------
class TestValidationSection:
    def test_validation_not_mapping_raises(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "validation: not-a-mapping\n"
        )
        with pytest.raises(ConfigValidationError, match="validation"):
            load(tmp_path, content)

    def test_negative_min_size_raises(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "validation:\n  min_size_bytes: -100\n"
        )
        with pytest.raises(ConfigValidationError, match="min_size_bytes"):
            load(tmp_path, content)

    def test_non_integer_min_size_raises(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "validation:\n  min_size_bytes: big\n"
        )
        with pytest.raises(ConfigValidationError, match="min_size_bytes"):
            load(tmp_path, content)

    def test_validation_defaults_applied(self, tmp_path):
        loader = load(tmp_path)
        vl = loader.validation
        assert vl["require_pdf_header"] == ConfigLoader.DEFAULT_REQUIRE_PDF_HEADER
        assert vl["min_size_bytes"] == ConfigLoader.DEFAULT_MIN_SIZE_BYTES
        assert vl["checksum_algorithm"] == ConfigLoader.DEFAULT_CHECKSUM_ALGORITHM


# ---------------------------------------------------------------------------
# Textbook validation (V6, V7, V8)
# ---------------------------------------------------------------------------
class TestTextbookValidation:
    def test_gseb_textbooks_not_list_raises(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "gseb:\n  textbooks: not-a-list\n"
        )
        with pytest.raises(ConfigValidationError, match="gseb.textbooks"):
            load(tmp_path, content)

    def test_gseb_entry_not_mapping_raises(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "gseb:\n  textbooks:\n    - just-a-string\n"
        )
        with pytest.raises(ConfigValidationError, match=r"gseb.textbooks\[0\]"):
            load(tmp_path, content)

    def test_gseb_missing_required_field_raises(self, tmp_path):
        # Missing "url" and "filename".
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "gseb:\n  textbooks:\n"
            "    - std: 10\n"
            "      subject: math\n"
            "      medium: gujarati\n"
            "      language: gu\n"
        )
        with pytest.raises(ConfigValidationError, match=r"gseb.textbooks\[0\]"):
            load(tmp_path, content)

    def test_gseb_valid_textbook_passes(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "gseb:\n  textbooks:\n"
            "    - std: 10\n"
            "      subject: math\n"
            "      medium: gujarati\n"
            "      language: gu\n"
            "      url: https://example.org/x.pdf\n"
            "      filename: 10_gu_math_x.pdf\n"
        )
        loader = load(tmp_path, content)
        tbs = loader.get_textbooks("gseb")
        assert len(tbs) == 1
        assert tbs[0]["std"] == 10

    def test_ncert_missing_required_field_raises(self, tmp_path):
        # Missing "code".
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "ncert:\n  textbooks:\n"
            "    - std: 10\n"
            "      subject: science\n"
            "      medium: english\n"
            "      language: en\n"
        )
        with pytest.raises(ConfigValidationError, match=r"ncert.textbooks\[0\]"):
            load(tmp_path, content)

    def test_ncert_valid_textbook_passes(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "ncert:\n  textbooks:\n"
            "    - code: kegy102\n"
            "      std: 10\n"
            "      subject: science\n"
            "      medium: english\n"
            "      language: en\n"
        )
        loader = load(tmp_path, content)
        assert len(loader.get_textbooks("ncert")) == 1

    def test_empty_textbooks_is_allowed(self, tmp_path):
        # Zero textbooks should NOT raise (only a warning) — V6 semantics.
        loader = load(tmp_path)
        assert loader.get_textbooks("gseb") == []
        assert loader.get_textbooks("ncert") == []


# ---------------------------------------------------------------------------
# NCERT template validation (V9)
# ---------------------------------------------------------------------------
class TestNcertTemplateValidation:
    def _with_ncert(self, tmp_path, ncert_yaml):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            f"ncert:\n{ncert_yaml}\n"
        )
        return load(tmp_path, content)

    def test_unknown_placeholder_in_url_template_raises(self, tmp_path):
        with pytest.raises(ConfigValidationError, match="url_template"):
            self._with_ncert(
                tmp_path,
                '  url_template: "https://x/{bogus}.pdf"\n',
            )

    def test_unknown_placeholder_in_filename_template_raises(self, tmp_path):
        with pytest.raises(ConfigValidationError, match="filename_template"):
            self._with_ncert(
                tmp_path,
                '  filename_template: "{oops}.pdf"\n',
            )

    def test_known_placeholders_are_accepted(self, tmp_path):
        ncert_yaml = (
            '  url_template: "https://ncert.nic.in/textbook/pdf/{code}.pdf"\n'
            '  filename_template: "{std}_{medium}_{subject}_{code}.pdf"\n'
        )
        loader = self._with_ncert(tmp_path, ncert_yaml)
        assert loader.ncert["url_template"].endswith("{code}.pdf")

    def test_ncert_template_defaults_applied(self, tmp_path):
        loader = load(tmp_path)
        assert "{code}" in loader.ncert["url_template"]
        assert "{code}" in loader.ncert["filename_template"]


# ---------------------------------------------------------------------------
# Alias canonicalisation (V10)
# ---------------------------------------------------------------------------
class TestAliasCanonicalisation:
    def test_chunk_size_bytes_aliased_to_chunk_size(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "download:\n  chunk_size_bytes: 16384\n"
        )
        loader = load(tmp_path, content)
        assert loader.download["chunk_size"] == 16384
        assert loader.download["chunk_size_bytes"] == 16384

    def test_chunk_size_takes_precedence_when_both_present(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "download:\n  chunk_size: 4096\n  chunk_size_bytes: 16384\n"
        )
        loader = load(tmp_path, content)
        # When both present, chunk_size wins.
        assert loader.download["chunk_size"] == 4096


# ---------------------------------------------------------------------------
# Accessor properties
# ---------------------------------------------------------------------------
class TestAccessors:
    def test_config_property_returns_full_dict(self, tmp_path):
        loader = load(tmp_path)
        cfg = loader.config
        assert cfg["version"] == "1.0"
        assert "general" in cfg
        assert "download" in cfg  # default-applied

    def test_section_accessors_return_dicts(self, tmp_path):
        loader = load(tmp_path)
        assert isinstance(loader.general, dict)
        assert isinstance(loader.download, dict)
        assert isinstance(loader.validation, dict)
        assert isinstance(loader.ncert, dict)
        assert isinstance(loader.gseb, dict)
        assert isinstance(loader.logging_config, dict)

    def test_content_root_returns_path(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: /data/CONTENT\n"
        )
        loader = load(tmp_path, content)
        assert isinstance(loader.content_root, Path)
        assert str(loader.content_root) == "/data/CONTENT" \
            or str(loader.content_root).replace("\\", "/") == "/data/CONTENT"

    def test_get_textbooks_is_case_insensitive(self, tmp_path):
        content = (
            'version: "1.0"\n'
            "general:\n  content_root: ./CONTENT\n"
            "gseb:\n  textbooks:\n"
            "    - std: 12\n"
            "      subject: physics\n"
            "      medium: gujarati\n"
            "      language: gu\n"
            "      url: https://example.org/p.pdf\n"
            "      filename: 12_gu_physics_p.pdf\n"
        )
        loader = load(tmp_path, content)
        assert loader.get_textbooks("GSEB") == loader.get_textbooks("gseb")
        assert loader.get_textbooks("Gseb")[0]["subject"] == "physics"

    def test_get_textbooks_unknown_board_returns_empty(self, tmp_path):
        loader = load(tmp_path)
        assert loader.get_textbooks("cbse") == []


# ---------------------------------------------------------------------------
# Logging section defaults
# ---------------------------------------------------------------------------
class TestLoggingDefaults:
    def test_logging_defaults_applied(self, tmp_path):
        loader = load(tmp_path)
        lg = loader.logging_config
        assert lg["level"] == ConfigLoader.DEFAULT_LOG_LEVEL
        assert lg["jsonl"] == ConfigLoader.DEFAULT_JSONL
        assert lg["human_readable"] == ConfigLoader.DEFAULT_HUMAN_READABLE
        assert lg["log_dir"] == ConfigLoader.DEFAULT_LOG_DIR


# ---------------------------------------------------------------------------
# Repr / smoke
# ---------------------------------------------------------------------------
class TestRepr:
    def test_repr_includes_path_and_version(self, tmp_path):
        path = write_config(tmp_path, MINIMAL_VALID_YAML)
        loader = ConfigLoader(path)
        r = repr(loader)
        assert "ConfigLoader" in r
        assert "1.0" in r


# ---------------------------------------------------------------------------
# End-to-end: a fully-specified realistic config round-trips through yaml + loader
# ---------------------------------------------------------------------------
class TestEndToEnd:
    def test_full_realistic_config_loads(self, tmp_path):
        data = {
            "version": "1.0",
            "general": {
                "content_root": "./CONTENT",
                "edf_metadata_dir": ".edf",
                "dry_run": False,
                "force_overwrite": False,
            },
            "download": {
                "max_retries": 5,
                "timeout_seconds": 60,
                "chunk_size_bytes": 16384,
                "backoff_base_seconds": 2,
                "user_agent": "TestAgent/1.0",
                "temp_dir": ".edf/tmp",
                "delay_seconds": 0.5,
            },
            "validation": {
                "require_pdf_header": True,
                "min_size_bytes": 2048,
                "checksum_algorithm": "sha256",
            },
            "ncert": {
                "url_template": "https://ncert.nic.in/textbook/pdf/{code}.pdf",
                "filename_template": "{std}_{medium}_{subject}_{code}.pdf",
                "textbooks": [
                    {
                        "code": "kegy102",
                        "std": 10,
                        "subject": "geography",
                        "medium": "english",
                        "language": "en",
                    }
                ],
            },
            "gseb": {
                "textbooks": [
                    {
                        "std": 10,
                        "subject": "math",
                        "medium": "gujarati",
                        "language": "gu",
                        "url": "https://gseb.org/m.pdf",
                        "filename": "10_gu_math_m.pdf",
                    }
                ],
            },
            "logging": {
                "level": "DEBUG",
                "jsonl": True,
                "human_readable": False,
                "log_dir": ".edf/logs",
            },
        }
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")

        loader = ConfigLoader(path)

        # Alias normalisation: chunk_size_bytes → chunk_size
        assert loader.download["chunk_size"] == 16384
        assert loader.is_dry_run is False
        assert loader.content_root == Path("./CONTENT")
        assert loader.logging_config["level"] == "DEBUG"
        assert len(loader.get_textbooks("ncert")) == 1
        assert len(loader.get_textbooks("gseb")) == 1
