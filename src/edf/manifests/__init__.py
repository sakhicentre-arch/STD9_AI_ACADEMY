"""
EDF-L1 Manifests Package.

Generates and maintains manifest.json and checksums.json
for the CONTENT repository.
"""

from src.edf.manifests.manager import ManifestManager

__all__ = ["ManifestManager"]
