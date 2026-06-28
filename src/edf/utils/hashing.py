"""
EDF-L1 Hashing Utilities.

Provides SHA-256 hashing for files and byte streams.
Used by the validation pipeline and checksum registry.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def sha256_file(file_path: Path | str, chunk_size: int = 8192) -> str:
    """
    Compute the SHA-256 checksum of a file.

    Reads the file in chunks to support large files without
    loading them entirely into memory.

    Args:
        file_path: Path to the file to hash.
        chunk_size: Read buffer size in bytes (default 8 KB).

    Returns:
        SHA-256 hex digest string (64 characters).

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If the file cannot be read.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """
    Compute the SHA-256 checksum of a bytes object.

    Args:
        data: Raw bytes to hash.

    Returns:
        SHA-256 hex digest string (64 characters).
    """
    return hashlib.sha256(data).hexdigest()


def sha256_stream(stream, chunk_size: int = 8192) -> str:
    """
    Compute the SHA-256 checksum from a readable stream.

    Reads from the current position until EOF. Does not
    seek back to the start.

    Args:
        stream: A file-like object supporting ``read(size)``.
        chunk_size: Read buffer size in bytes (default 8 KB).

    Returns:
        SHA-256 hex digest string (64 characters).
    """
    h = hashlib.sha256()
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def compare_checksums(
    actual: str,
    expected: Optional[str] = None,
) -> bool:
    """
    Compare an actual checksum against an expected value.

    Args:
        actual: Computed SHA-256 hex digest.
        expected: Expected SHA-256 hex digest, or None (always returns True).

    Returns:
        True if checksums match, or expected is None.
    """
    if expected is None:
        return True
    return actual.lower() == expected.lower()
