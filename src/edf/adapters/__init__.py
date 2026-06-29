"""
EDF-L1 Adapters Package.

Each source (GSEB, NCERT) implements a common BaseAdapter interface.
New sources require only a new adapter class conforming to this interface.
"""

from src.edf.adapters.base import BaseAdapter
from src.edf.adapters.gseb import GSEBAdapter
from src.edf.models.data import DownloadDescriptor

__all__ = ["BaseAdapter", "DownloadDescriptor", "GSEBAdapter"]
