"""
EDF-L1 PDF Validation Utilities.

Provides PDF header validation, MIME type checking,
and page count estimation placeholders.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# PDF magic bytes: %PDF- (5 bytes, ASCII)
PDF_MAGIC = b"%PDF-"

# Valid PDF MIME types
PDF_MIME_TYPES = frozenset({
    "application/pdf",
})


def validate_pdf_header(file_path: Path | str) -> bool:
    """
    Validate that a file starts with the PDF magic bytes.

    Reads the first 5 bytes and checks for the ``%PDF-`` signature.

    Args:
        file_path: Path to the file to validate.

    Returns:
        True if the file has a valid PDF header.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If the file cannot be read.
    """
    with open(file_path, "rb") as f:
        header = f.read(len(PDF_MAGIC))
    return header == PDF_MAGIC


def validate_mime_type(file_path: Path | str) -> bool:
    """
    Validate the MIME type of a file using magic byte detection.

    Uses the ``mimetypes`` module (no external dependency).
    For PDFs, also cross-checks the PDF header.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the MIME type is ``application/pdf``.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    import mimetypes
    mime, _ = mimetypes.guess_type(str(file_path))
    # If MIME can't be guessed from extension, fall back to header check.
    if mime is None:
        return validate_pdf_header(file_path)
    return mime in PDF_MIME_TYPES


def get_page_count(file_path: Path | str) -> Optional[int]:
    """
    Estimate or count the number of pages in a PDF.

    Placeholder — requires PDF parsing library (e.g., PyMuPDF, pypdf).
    Will be implemented in a future phase if needed.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Page count as integer, or None if detection is not available.
    """
    # TODO: Implement page count detection.
    # This requires a PDF library (PyMuPDF, pypdf, etc.)
    return None


def validate_pdf_size(
    file_path: Path | str,
    min_bytes: int = 10240,
    max_bytes: Optional[int] = None,
) -> bool:
    """
    Validate that a PDF file meets size constraints.

    Args:
        file_path: Path to the PDF file.
        min_bytes: Minimum file size in bytes (default 10 KB).
        max_bytes: Maximum file size in bytes, or None for no upper limit.

    Returns:
        True if the file meets all size constraints.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    import os
    size = os.path.getsize(file_path)
    if size < min_bytes:
        return False
    if max_bytes is not None and size > max_bytes:
        return False
    return True
