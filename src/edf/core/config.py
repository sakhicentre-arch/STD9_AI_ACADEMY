"""
EDF-L1 Config Loader.

Loads, validates, and provides typed access to the config.yaml configuration.
Handles missing values with clear error messages and sensible defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


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
        self._validate()

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
        return Path(self.general.get("content_root", "./CONTENT"))

    @property
    def edf_metadata_dir(self) -> str:
        """Return the metadata directory name within content root."""
        return self.general.get("edf_metadata_dir", ".edf")

    @property
    def is_dry_run(self) -> bool:
        """Return True if dry-run mode is enabled."""
        return self.general.get("dry_run", False)

    @property
    def is_force_overwrite(self) -> bool:
        """Return True if force-overwrite mode is enabled."""
        return self.general.get("force_overwrite", False)

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
            yaml.YAMLError: If the YAML is malformed.
        """
        # TODO: Implement YAML file reading and parsing.
        # if not self._config_path.exists():
        #     raise FileNotFoundError(f"Config file not found: {self._config_path}")
        # with open(self._config_path, "r", encoding="utf-8") as f:
        #     self._raw = yaml.safe_load(f) or {}
        self._raw = {"version": "1.0"}  # Placeholder for Phase 1 bootstrap

    def _validate(self) -> None:
        """
        Validate the loaded configuration.

        Checks for required fields, correct types, and logical consistency.

        Raises:
            ConfigValidationError: On validation failure.
        """
        # TODO: Implement validation logic.
        # - Check version is present and supported
        # - Check general.content_root is present
        # - Check at least one adapter is enabled
        # - Check download settings are valid ranges
        # - Check ncert/gseb textbook entries have required fields
        pass

    def __repr__(self) -> str:
        return (
            f"ConfigLoader(path={self._config_path!s}, "
            f"version={self.version!r})"
        )
