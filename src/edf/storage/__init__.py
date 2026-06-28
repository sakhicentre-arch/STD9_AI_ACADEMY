"""
EDF-L1 Storage Package.

Manages filesystem operations within the CONTENT directory:
path resolution, duplicate detection, atomic file placement.
"""

from src.edf.storage.manager import StorageManager

__all__ = ["StorageManager"]
