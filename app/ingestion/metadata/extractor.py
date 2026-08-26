"""Document metadata extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.schemas.common import DocumentReference, ParsedDocument


def infer_document_type(filename: str) -> str:
    """Infer a document type label from the file extension."""
    extension = Path(filename).suffix.lower().lstrip(".")
    mapping = {
        "pdf": "pdf",
        "docx": "docx",
        "md": "markdown",
        "markdown": "markdown",
        "txt": "text",
        "html": "html",
        "htm": "html",
    }
    return mapping.get(extension, extension or "unknown")


def extract_metadata(
    reference: DocumentReference,
    parsed: ParsedDocument,
) -> dict[str, Any]:
    """Merge reference and parsed metadata into an indexable metadata dict."""
    document_type = infer_document_type(reference.filename)
    metadata: dict[str, Any] = {
        "stable_id": reference.stable_id,
        "filename": reference.filename,
        "title": parsed.title,
        "source": reference.source,
        "source_url": reference.source_url,
        "document_type": document_type,
        "checksum": reference.checksum,
        "modified_at": reference.modified_at.isoformat() if reference.modified_at else None,
        "section_count": len(parsed.sections),
    }
    metadata.update(reference.metadata)
    metadata.update(parsed.metadata)
    return metadata
