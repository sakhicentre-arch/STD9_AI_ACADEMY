"""
EDF-L1 Logging Package.

Provides structured dual-output logging:
- JSON lines (.jsonl) for machine consumption
- Human-readable (.log) for operators
"""

from src.edf.logging.logger import EDFLogger

__all__ = ["EDFLogger"]
