"""
EDF-L1 Adapters Package.

Each source (GSEB, NCERT, ...) implements a common BaseAdapter interface.
New sources require only a new adapter class conforming to this interface
and registration via :class:`AdapterRegistry`.

The :func:`default_registry` factory returns a registry preloaded with the
built-in adapters.
"""

from src.edf.adapters.base import BaseAdapter
from src.edf.adapters.gseb import GSEBAdapter
from src.edf.adapters.ncert import NCERTAdapter
from src.edf.adapters.registry import AdapterRegistry, default_registry
from src.edf.models.data import DownloadDescriptor

__all__ = [
    "BaseAdapter",
    "DownloadDescriptor",
    "GSEBAdapter",
    "NCERTAdapter",
    "AdapterRegistry",
    "default_registry",
]
