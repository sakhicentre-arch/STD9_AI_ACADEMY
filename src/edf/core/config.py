"""
EDF-L1 Config Loader.

Loads, validates, and provides typed access to the config.yaml configuration.
Handles missing values with clear error messages and sensible defaults.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when config.yaml fails validation."""
    pass


class ConfigLoader:
    """
    Loads and validates the EDF-L1 configuration file.

    The configuration is loaded once at pipeline start and passed to all
    components via dependency injection. This class provides typed accessors
    for each configuration section.

    Dependency Injection:
        ConfigLoader is instantiated early in the pipeline and injected into
        adapters, managers, and the orchestrator.

    Example::

        loader = ConfigLoader("config.yaml")
        config = loader.config
        print(config.general["content_root"])
        print(config.download["max_retries"])
    """

    # ---------------------------------------------------------------------------
    # Single source of truth for defaults
    # ---------------------------------------------------------------------------
    DEFAULT_VERSION = "1.0"
    DEFAULT_CONTENT_ROOT = "./CONTENT"
    DEFAULT_EDF_METADATA_DIR = ".edf"
    DEFAULT_DRY_RUN = False
    DEFAULT_FORCE_OVERWRITE = False
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT_SECONDS = 120
    DEFAULT_CHUNK_SIZE_BYTES = 8192
    DEFAULT_BACKOFF_BASE_SECONDS = 1
    DEFAULT_USER_AGENT = "STD9-AI-Academy/EDF-L1 (educational download)"
    DEFAULT_TEMP_DIR = ".edf/tmp"
    DEFAULT_DELAY_SECONDS = 1.0
    DEFAULT_REQUIRE_PDF_HEADER = True
    DEFAULT_MIN_SIZE_BYTES = 10240
    DEFAULT_CHECKSUM_ALGORITHM = "sha256"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_JSONL = True
    DEFAULT_HUMAN_READABLE = True
    DEFAULT_LOG_DIR = ".edf/logs"

    # GSEB required per-textbook fields (copied verbatim from gseb.py:109)
    GSEB_REQUIRED_FIELDS = ["std", "subject", "medium", "language", "url", "filename"]

    # NCERT required per-textbook fields (copied verbatim from ncert.py:54)
    NCERT_REQUIRED_FIELDS = ["code", "std", "subject", "medium", "language"]

    # NCERT template placeholder names (from ncert.py:49-50 docstrings)
    NCERT_KNOWN_PLACEHOLDERS = {"code", "std", "subject", "medium", "language"}

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        """
        Load and validate the configuration file.

        Args:
            config_path: Path to the YAML configuration file.

        Raises:
            FileNotFoundError: If config file does not exist.
            ConfigValidationError: If config is malformed or missing required fields.
        """
        self._config_path = Path(config_path)
        self._raw: Dict[str, Any] = {}
        self._load()
        self._pre_defaults = dict(self._raw)  # snapshot for structural validation
        self._apply_defaults()
        self._validate()
        self._canonicalize_aliases()

    @property
    def config(self) -> Dict[str, Any]:
        """Return the full raw configuration dictionary."""
        return self._raw

    @property
    def version(self) -> str:
        """Return the config schema version."""
        return self._raw.get("version", "unknown")

    @property
    def general(self) -> Dict[str, Any]:
        """Return the general settings section."""
        return self._raw.get("general", {})

    @property
    def download(self) -> Dict[str, Any]:
        """Return the download settings section."""
        return self._raw.get("download", {})

    @property
    def validation(self) -> Dict[str, Any]:
        """Return the validation settings section."""
        return self._raw.get("validation", {})

    @property
    def ncert(self) -> Dict[str, Any]:
        """Return the NCERT adapter configuration section."""
        return self._raw.get("ncert", {})

    @property
    def gseb(self) -> Dict[str, Any]:
        """Return the GSEB adapter configuration section."""
        return self._raw.get("gseb", {})

    @property
    def logging_config(self) -> Dict[str, Any]:
        """Return the logging configuration section."""
        return self._raw.get("logging", {})

    @property
    def content_root(self) -> Path:
        """Return the resolved content root directory path."""
        return Path(self.general.get("content_root", self.DEFAULT_CONTENT_ROOT))

    @property
    def edf_metadata_dir(self) -> str:
        """Return the metadata directory name within content root."""
        return self.general.get("edf_metadata_dir", self.DEFAULT_EDF_METADATA_DIR)

    @property
    def is_dry_run(self) -> bool:
        """Return True if dry-run mode is enabled."""
        return bool(self.general.get("dry_run", self.DEFAULT_DRY_RUN))

    @property
    def is_force_overwrite(self) -> bool:
        """Return True if force-overwrite mode is enabled."""
        return bool(self.general.get("force_overwrite", self.DEFAULT_FORCE_OVERWRITE))

    def get_textbooks(self, board: str) -> List[Dict[str, Any]]:
        """
        Get the textbook configuration list for a specific board.

        Args:
            board: Board name (e.g., "gseb", "ncert").

        Returns:
            List of textbook configuration dictionaries.
        """
        board_config = self._raw.get(board.lower(), {})
        return board_config.get("textbooks", [])

    def _load(self) -> None:
        """
        Load the YAML configuration file from disk.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ConfigValidationError: If the YAML is malformed or root is not a mapping.
        """
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self._config_path}"
            )
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ConfigValidationError(
                f"Malformed YAML in {self._config_path}: {exc}"
            ) from exc

        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            raise ConfigValidationError(
                f"Config root must be a mapping, got {type(loaded).__name__}"
            )
        self._raw = loaded

    def _ensure_dict_section(self, key: str) -> dict:
        """Return ``self._raw[key]`` as a dict, replacing non-mappings.

        If the key is missing, an empty dict is created.  If the existing
        value is not a dict (e.g. a string from a malformed config), it is
        replaced with an empty dict so that downstream ``setdefault`` calls
        do not raise ``AttributeError``.  The real type mismatch is caught
        later by ``_validate()`` which raises ``ConfigValidationError``.
        """
        existing = self._raw.get(key)
        if existing is None or not isinstance(existing, dict):
            self._raw[key] = {}
        return self._raw[key]

    def _apply_defaults(self) -> None:
        """
        Apply default values for optional sections and keys.

        After _load() reads the raw YAML, this method fills in defaults so that
        downstream consumers can rely on keys being present.  Defaults are the
        single source of truth (class-level constants); consumer-level
        ``.get(..., fallback)`` calls remain for defence-in-depth but should
        never trigger with a validated config.
        """
        # general
        general = self._ensure_dict_section("general")
        general.setdefault("content_root", self.DEFAULT_CONTENT_ROOT)
        general.setdefault("edf_metadata_dir", self.DEFAULT_EDF_METADATA_DIR)
        general.setdefault("dry_run", self.DEFAULT_DRY_RUN)
        general.setdefault("force_overwrite", self.DEFAULT_FORCE_OVERWRITE)

        # download
        dl = self._ensure_dict_section("download")
        dl.setdefault("max_retries", self.DEFAULT_MAX_RETRIES)
        dl.setdefault("backoff_base_seconds", self.DEFAULT_BACKOFF_BASE_SECONDS)
        dl.setdefault("timeout_seconds", self.DEFAULT_TIMEOUT_SECONDS)
        dl.setdefault("user_agent", self.DEFAULT_USER_AGENT)
        dl.setdefault("temp_dir", self.DEFAULT_TEMP_DIR)
        dl.setdefault("delay_seconds", self.DEFAULT_DELAY_SECONDS)

        # validation
        vl = self._ensure_dict_section("validation")
        vl.setdefault("require_pdf_header", self.DEFAULT_REQUIRE_PDF_HEADER)
        vl.setdefault("min_size_bytes", self.DEFAULT_MIN_SIZE_BYTES)
        vl.setdefault("checksum_algorithm", self.DEFAULT_CHECKSUM_ALGORITHM)

        # logging
        lg = self._ensure_dict_section("logging")
        lg.setdefault("level", self.DEFAULT_LOG_LEVEL)
        lg.setdefault("jsonl", self.DEFAULT_JSONL)
        lg.setdefault("human_readable", self.DEFAULT_HUMAN_READABLE)
        lg.setdefault("log_dir", self.DEFAULT_LOG_DIR)

        # ncert — board-level defaults
        ncert = self._ensure_dict_section("ncert")
        ncert.setdefault("url_template", "https://ncert.nic.in/textbook/pdf/{code}.pdf")
        ncert.setdefault("filename_template", "{std}_{medium}_{subject}_{code}.pdf")

        # gseb — ensure textbooks list exists
        self._ensure_dict_section("gseb").setdefault("textbooks", [])

    def _validate(self) -> None:
        """
        Validate the loaded configuration.

        Checks for required fields, correct types, and logical consistency.
        Implements rules V1–V10 from the Phase 7 Technical Design §2.2.2.

        Raises:
            ConfigValidationError: On validation failure.
        """

        # V1 — version present and == "1.0"
        version = self._raw.get("version")
        if version is None:
            raise ConfigValidationError(
                "Missing required key 'version'. "
                f"Expected '1.0' (see config.yaml.example)."
            )
        if not isinstance(version, str) or version != self.DEFAULT_VERSION:
            raise ConfigValidationError(
                f"Unsupported config version '{version!r}'. "
                f"Expected the string '{self.DEFAULT_VERSION}'."
            )

        # V2 — general is a mapping
        general = self._pre_defaults.get("general")
        if general is not None and not isinstance(general, dict):
            raise ConfigValidationError(
                "'general' must be a mapping, got "
                f"{type(general).__name__}"
            )

        # V3 — general.content_root is a non-empty string
        # When general was absent, _apply_defaults() already injected
        # defaults into self._raw["general"]; read from there.
        general = general or self._raw.get("general", {})
        content_root = general.get("content_root")
        if not content_root or not isinstance(content_root, str) or not content_root.strip():
            raise ConfigValidationError(
                "'general.content_root' must be a non-empty string."
            )

        # V4 — download (if present) is a mapping; numeric fields are ints >= 0
        dl_raw = self._pre_defaults.get("download")
        if dl_raw is not None:
            if not isinstance(dl_raw, dict):
                raise ConfigValidationError(
                    "'download' must be a mapping, got "
                    f"{type(dl_raw).__name__}"
                )
            self._validate_download_numeric(self._raw["download"], "download")

        # V5 — validation (if present) is a mapping; min_size_bytes int >= 0
        vl_raw = self._pre_defaults.get("validation")
        if vl_raw is not None:
            if not isinstance(vl_raw, dict):
                raise ConfigValidationError(
                    "'validation' must be a mapping, got "
                    f"{type(vl_raw).__name__}"
                )
            vl = self._raw["validation"]
            if "min_size_bytes" in vl:
                self._check_non_negative_int(vl, "min_size_bytes", "validation")
            if "max_size_bytes" in vl and vl["max_size_bytes"] is not None:
                self._check_non_negative_int(vl, "max_size_bytes", "validation")

        # V6 — structural usability check
        # Error only if config is structurally unusable (no general section
        # handled above).  Zero textbooks is a WARNING, not a hard error,
        # preserving Phase 5/6 adapter semantics.
        gseb_tbs = self._raw.get("gseb", {}).get("textbooks", [])
        ncert_tbs = self._raw.get("ncert", {}).get("textbooks", [])
        if not gseb_tbs and not ncert_tbs:
            logger.warning(
                "No textbooks configured for any board. "
                "The pipeline will have nothing to download."
            )

        # V7 — GSEB per-textbook required fields
        self._validate_textbook_entries(
            textbooks=gseb_tbs,
            required_fields=self.GSEB_REQUIRED_FIELDS,
            board="gseb",
        )

        # V8 — NCERT per-textbook required fields
        self._validate_textbook_entries(
            textbooks=ncert_tbs,
            required_fields=self.NCERT_REQUIRED_FIELDS,
            board="ncert",
        )

        # V9 — NCERT template placeholders
        self._validate_ncert_templates()

    def _canonicalize_aliases(self) -> None:
        """
        Canonicalize configuration aliases.

        V10 — chunk_size / chunk_size_bytes: accept either form and
        normalise so the downloader reads consistently.  The downloader
        reads ``chunk_size`` (downloader.py:209), but config.yaml.example
        documents ``chunk_size_bytes``.
        """
        dl = self._raw.setdefault("download", {})
        if "chunk_size_bytes" in dl and "chunk_size" not in dl:
            dl["chunk_size"] = dl["chunk_size_bytes"]
            logger.debug(
                "Aliased 'chunk_size_bytes' → 'chunk_size' = %s",
                dl["chunk_size"],
            )
        elif "chunk_size_bytes" in dl and "chunk_size" in dl:
            # Both present — prefer chunk_size (the downloader key),
            # log a warning about the duplicate.
            logger.warning(
                "Both 'chunk_size' and 'chunk_size_bytes' are set in "
                "'download'. Using 'chunk_size' (%s). "
                "Remove 'chunk_size_bytes' to silence this warning.",
                dl["chunk_size"],
            )

    # ------------------------------------------------------------------
    # Validation helpers (private)
    # ------------------------------------------------------------------

    def _validate_download_numeric(self, section: dict, prefix: str) -> None:
        """Validate that numeric download fields are integers >= 0.

        ``delay_seconds`` is the exception: it accepts floats (e.g. 0.5)
        to allow sub-second throttling delays.
        """
        for key in ("max_retries", "timeout_seconds", "chunk_size",
                     "chunk_size_bytes", "backoff_base_seconds"):
            if key in section and section[key] is not None:
                self._check_non_negative_int(section, key, prefix)
        # delay_seconds accepts both int and float (sub-second delays).
        if "delay_seconds" in section and section["delay_seconds"] is not None:
            self._check_non_negative_number(section, "delay_seconds", prefix)

    def _check_non_negative_int(
        self, section: dict, key: str, prefix: str
    ) -> None:
        """Raise ConfigValidationError if ``section[key]`` is not an int >= 0."""
        value = section.get(key)
        full_key = f"{prefix}.{key}" if prefix else key
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigValidationError(
                f"'{full_key}' must be an integer, got "
                f"{type(value).__name__}"
            )
        if value < 0:
            raise ConfigValidationError(
                f"'{full_key}' must be >= 0, got {value}"
            )

    def _check_non_negative_number(
        self, section: dict, key: str, prefix: str
    ) -> None:
        """Raise ConfigValidationError if ``section[key]`` is not a number >= 0."""
        value = section.get(key)
        full_key = f"{prefix}.{key}" if prefix else key
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConfigValidationError(
                f"'{full_key}' must be a number, got "
                f"{type(value).__name__}"
            )
        if value < 0:
            raise ConfigValidationError(
                f"'{full_key}' must be >= 0, got {value}"
            )

    def _validate_textbook_entries(
        self,
        textbooks: list,
        required_fields: list,
        board: str,
    ) -> None:
        """
        Validate per-textbook required fields.

        Raises:
            ConfigValidationError: If any entry is missing a required field,
                naming the board, index, and field.
        """
        if not isinstance(textbooks, list):
            raise ConfigValidationError(
                f"'{board}.textbooks' must be a list, got "
                f"{type(textbooks).__name__}"
            )
        for idx, entry in enumerate(textbooks):
            if not isinstance(entry, dict):
                raise ConfigValidationError(
                    f"'{board}.textbooks[{idx}]' must be a mapping, got "
                    f"{type(entry).__name__}"
                )
            missing = [
                f for f in required_fields
                if not entry.get(f)
            ]
            if missing:
                raise ConfigValidationError(
                    f"'{board}.textbooks[{idx}]: missing "
                    f"{', '.join(missing)}"
                )

    def _validate_ncert_templates(self) -> None:
        """
        Validate NCERT URL and filename templates contain only known placeholders.

        Known placeholders: {code}, {std}, {subject}, {medium}, {language}.

        Raises:
            ConfigValidationError: If an unknown placeholder is found.
        """
        ncert = self._raw.get("ncert", {})

        # Collect all placeholder names used across both templates.
        for tmpl_key in ("url_template", "filename_template"):
            tmpl = ncert.get(tmpl_key)
            if tmpl and isinstance(tmpl, str):
                placeholders = set(re.findall(r'\{(\w+)\}', tmpl))
                unknown = placeholders - self.NCERT_KNOWN_PLACEHOLDERS
                if unknown:
                    raise ConfigValidationError(
                        f"'ncert.{tmpl_key}' contains unknown placeholder(s): "
                        f"{', '.join(sorted(unknown))}. "
                        f"Allowed: {', '.join(sorted(self.NCERT_KNOWN_PLACEHOLDERS))}"
                    )

    def __repr__(self) -> str:
        return (
            f"ConfigLoader(path={self._config_path!s}, "
            f"version={self.version!r})"
        )
