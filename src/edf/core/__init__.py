"""
EDF-L1 Core Package.

Orchestrates the full pipeline and provides configuration management.
"""

from src.edf.core.config import ConfigLoader
from src.edf.core.pipeline import PipelineOrchestrator

__all__ = ["ConfigLoader", "PipelineOrchestrator"]
