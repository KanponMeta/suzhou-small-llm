"""Document parsing service for PDF, Markdown, and plain text files."""
import os
import tempfile
from pathlib import Path

import fitz  # PyMuPDF


def parse_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def parse_markdown(file_path: str) -> str:
    """Read a Markdown file as plain text."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_text(file_path: str) -> str:
    """Read a plain text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


SUPPORTED_TYPES = {
    "pdf": parse_pdf,
    "md": parse_markdown,
    "txt": parse_text,
}


def get_file_type(filename: str) -> str | None:
    """Determine file type from extension. Returns None if unsupported."""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "markdown":
        ext = "md"
    return ext if ext in SUPPORTED_TYPES else None


def parse_document(file_path: str, file_type: str) -> str:
    """Parse a document file and return its text content.

    Args:
        file_path: Path to the file on disk.
        file_type: One of 'pdf', 'md', 'txt'.

    Returns:
        Extracted text content.

    Raises:
        ValueError: If file_type is not supported.
    """
    parser = SUPPORTED_TYPES.get(file_type)
    if parser is None:
        raise ValueError(
            f"Unsupported file type: {file_type}. "
            f"Supported: {list(SUPPORTED_TYPES.keys())}"
        )
    return parser(file_path)
