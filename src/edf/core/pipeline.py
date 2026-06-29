"""
EDF-L1 Pipeline Orchestrator.

Sequences the full EDF-L1 pipeline:
load config → pre-flight verify → dedup → download → validate → manifest → log.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from src.edf.models.data import PreflightIssue, RunSummary

if TYPE_CHECKING:
    from src.edf.core.config import ConfigLoader
    from src.edf.logging.logger import EDFLogger

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the EDF-L1 download pipeline.

    Responsibilities:
        - Coordinate pipeline phases (config → verify → dedup → download → manifest)
        - Manage component lifecycle (initialize → run → shutdown)
        - Aggregate results and produce run summaries
        - Handle fatal vs recoverable errors at the pipeline level

    Dependency Injection:
        Receives ConfigLoader and EDFLogger via constructor or ``initialize()``.
        Adapters and managers are injected in Phase 2+.

    Example::

        orchestrator = PipelineOrchestrator()
        orchestrator.initialize(config_loader, logger_instance)
        result = orchestrator.run()
        orchestrator.shutdown()
    """

    def __init__(self) -> None:
        """
        Create a PipelineOrchestrator instance.

        Components are not initialized until ``initialize()`` is called.
        """
        self._config: Optional[ConfigLoader] = None
        self._logger: Optional[EDFLogger] = None
        self._initialized: bool = False

    def initialize(
        self,
        config_loader: ConfigLoader,
        logger_instance: EDFLogger,
    ) -> None:
        """
        Initialize the orchestrator with required dependencies.

        Args:
            config_loader: Loaded and validated configuration.
            logger_instance: Configured EDFLogger instance.
        """
        self._config = config_loader
        self._logger = logger_instance
        self._initialized = True
        logger.info("PipelineOrchestrator initialized")

    def run(self) -> dict:
        """
        Execute the full EDF-L1 pipeline.

        Pipeline phases:
            0. Inventory — scan existing CONTENT files (first run only)
            1. Pre-flight — adapter verification (GSEB URL check)
            2. Collect — gather download descriptors from adapters
            3. Dedup — skip files already present
            4. Download — download and validate each file
            5. Manifest — update manifest.json and checksums.json
            6. Summary — write run summary log

        Returns:
            Dictionary with run results including exit code, counts, and summary.

        Raises:
            RuntimeError: If the orchestrator has not been initialized.
        """
        if not self._initialized:
            raise RuntimeError(
                "PipelineOrchestrator not initialized. "
                "Call initialize() before run()."
            )

        logger.info("Pipeline started")

        run_id = self._logger.run_id if self._logger else ""

        # --- Initialize components ---
        from src.edf.storage.manager import StorageManager
        from src.edf.manifests.manager import ManifestManager
        from src.edf.adapters.registry import default_registry
        from src.edf.core.downloader import DownloadPipeline

        config = self._config.config
        storage = StorageManager(
            content_root=self._config.content_root,
            edf_dir=self._config.edf_metadata_dir,
        )
        manifest = ManifestManager(storage_manager=storage)
        manifest.load_existing()

        # Board discovery is registry-driven: the orchestrator is board-agnostic
        # and no longer hardcodes any concrete adapter. Each enabled board's
        # adapter is obtained from the registry and instantiated lazily.
        registry = default_registry()
        download_pipeline = DownloadPipeline(
            storage_manager=storage,
            manifest_manager=manifest,
            config=config,
        )

        result = {
            "exit_code": 0,
            "attempted": 0,
            "succeeded": 0,
            "skipped": 0,
            "failed": 0,
            "phases": {},
        }

        # --- Phase 0: Inventory ---
        try:
            discovered = manifest.discover_existing_files()
            logger.info(
                "Phase 0 (Inventory): discovered %d existing file(s)",
                len(discovered),
            )
            result["phases"]["inventory"] = {
                "status": "ok",
                "discovered": len(discovered),
            }
        except Exception as exc:
            logger.error("Phase 0 (Inventory) failed: %s", exc)
            result["phases"]["inventory"] = {
                "status": "error",
                "error": str(exc),
            }

        # --- Resolve enabled adapters via the registry ---
        enabled_boards = registry.enabled_boards(config, registry.list_adapters())
        adapters = [
            registry.create(board, config=config) for board in enabled_boards
        ]

        # --- Phase 1: Pre-flight (across all enabled adapters) ---
        try:
            preflight_issues = []
            for adapter in adapters:
                preflight_issues.extend(adapter.pre_flight())
            has_errors = any(
                i.severity.value == "ERROR" for i in preflight_issues
            )
            result["phases"]["preflight"] = {
                "status": "error" if has_errors else "ok",
                "issues": len(preflight_issues),
                "errors": sum(
                    1 for i in preflight_issues if i.severity.value == "ERROR"
                ),
                "warnings": sum(
                    1 for i in preflight_issues
                    if i.severity.value in ("WARNING", "INFO")
                ),
            }
            if has_errors:
                logger.error(
                    "Phase 1 (Pre-flight): %d error(s) — aborting pipeline",
                    result["phases"]["preflight"]["errors"],
                )
                result["exit_code"] = 2
                self._cleanup(manifest, run_id)
                return result
            logger.info(
                "Phase 1 (Pre-flight): %d issue(s) — proceeding",
                len(preflight_issues),
            )
        except Exception as exc:
            logger.error("Phase 1 (Pre-flight) failed: %s", exc)
            result["phases"]["preflight"] = {
                "status": "error",
                "error": str(exc),
            }
            result["exit_code"] = 2
            self._cleanup(manifest, run_id)
            return result

        # --- Phase 2: Collect descriptors (merged across all adapters) ---
        try:
            descriptors = []
            for adapter in adapters:
                descriptors.extend(adapter.get_descriptors())
            logger.info(
                "Phase 2 (Collect): %d descriptor(s)",
                len(descriptors),
            )
            result["phases"]["collect"] = {
                "status": "ok",
                "descriptors": len(descriptors),
            }
        except Exception as exc:
            logger.error("Phase 2 (Collect) failed: %s", exc)
            result["phases"]["collect"] = {"status": "error", "error": str(exc)}
            result["exit_code"] = 2
            self._cleanup(manifest, run_id)
            return result

        # --- Phase 3+4+5: Download, Validate, Store, Manifest ---
        if not descriptors:
            logger.info("No descriptors — skipping download phases")
            result["phases"]["download"] = {
                "status": "ok",
                "descriptors": 0,
            }
        else:
            try:
                force = self._config.is_force_overwrite
                summary = download_pipeline.run(
                    descriptors=descriptors,
                    run_id=run_id,
                    force=force,
                )
                result["attempted"] = summary.attempted
                result["succeeded"] = summary.succeeded
                result["skipped"] = summary.skipped
                result["failed"] = summary.failed
                result["exit_code"] = summary.exit_code
                result["phases"]["download"] = {
                    "status": "ok",
                    "attempted": summary.attempted,
                    "succeeded": summary.succeeded,
                    "skipped": summary.skipped,
                    "failed": summary.failed,
                    "duration": summary.duration_seconds,
                }
            except Exception as exc:
                logger.error("Phase 3-5 (Download pipeline) failed: %s", exc)
                result["phases"]["download"] = {
                    "status": "error",
                    "error": str(exc),
                }
                result["exit_code"] = 2

        # --- Phase 6: Persist manifest ---
        try:
            manifest.save(run_id=run_id)
            result["phases"]["manifest"] = {
                "status": "ok",
                "entries": manifest.entry_count,
            }
        except Exception as exc:
            logger.error("Phase 6 (Manifest save) failed: %s", exc)
            result["phases"]["manifest"] = {
                "status": "error",
                "error": str(exc),
            }

        # --- Phase 7: Summary ---
        result["phases"]["summary"] = {
            "exit_code": result["exit_code"],
            "total_attempted": result["attempted"],
            "total_succeeded": result["succeeded"],
            "total_skipped": result["skipped"],
            "total_failed": result["failed"],
        }

        if result["exit_code"] == 0:
            logger.info("Pipeline completed successfully")
        elif result["exit_code"] == 1:
            logger.warning("Pipeline completed with partial failures")
        else:
            logger.error("Pipeline failed")

        return result

    def _cleanup(self, manifest, run_id: str) -> None:
        """Best-effort cleanup on pipeline abort."""
        try:
            manifest.save(run_id=run_id)
        except Exception:
            pass

    def shutdown(self) -> None:
        """
        Clean up resources after pipeline execution.

        Closes HTTP sessions, flushes log buffers, etc.
        """
        logger.info("PipelineOrchestrator shutdown complete")
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Return True if the orchestrator has been initialized."""
        return self._initialized

    def __repr__(self) -> str:
        state = "initialized" if self._initialized else "uninitialized"
        return f"PipelineOrchestrator({state})"
