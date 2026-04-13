"""Reader for document formats using Docling: PDF, DOCX, PPTX, XLSX, HTML."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".html", ".htm"}


def can_handle(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


def read(file_path: str) -> Tuple[str, Optional[object], dict]:
    """
    Read a document file using Docling and return (markdown_text, docling_document, metadata).
    Falls back to raw text extraction on error.
    """
    path = Path(file_path)
    metadata = {
        "reader": "docling",
        "format": path.suffix.lower(),
        "file_name": path.name,
    }

    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(path))
        docling_doc = result.document

        markdown_content = result.document.export_to_markdown()

        if not markdown_content or not markdown_content.strip():
            logger.warning("Docling returned empty content for %s, falling back to text extraction", path.name)
            return _fallback_read(file_path, metadata)

        metadata["pages"] = getattr(result.document, "num_pages", None)
        metadata["conversion"] = "docling"

        return markdown_content, docling_doc, metadata

    except ImportError:
        logger.warning("Docling not installed. Install with: pip install docling")
        return _fallback_read(file_path, metadata)
    except Exception as e:
        logger.warning("Docling failed for %s: %s. Falling back.", path.name, e)
        return _fallback_read(file_path, metadata)


def _fallback_read(file_path: str, metadata: dict) -> Tuple[str, None, dict]:
    """Fallback: try to read as plain text."""
    path = Path(file_path)
    metadata["conversion"] = "fallback_text"

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            content = path.read_text(encoding=encoding)
            metadata["encoding"] = encoding
            return content, None, metadata
        except (UnicodeDecodeError, Exception):
            continue

    return f"[Could not read file: {path.name}]", None, metadata
