"""PDF document parser using PyMuPDF."""

from __future__ import annotations

import fitz

from app.ingestion.parsers.base import DocumentParser
from app.schemas.common import ParsedDocument, RawDocument


class PdfParser(DocumentParser):
    """Extract text and page-level sections from PDF files."""

    def supports(self, content_type: str, filename: str) -> bool:
        return filename.lower().endswith(".pdf") or content_type in {
            "application/pdf",
            "application/x-pdf",
        }

    def parse(self, raw: RawDocument) -> ParsedDocument:
        sections: list[dict[str, object]] = []
        text_parts: list[str] = []

        with fitz.open(stream=raw.content, filetype="pdf") as document:
            metadata = {
                "page_count": document.page_count,
                "author": document.metadata.get("author"),
                "subject": document.metadata.get("subject"),
                "creator": document.metadata.get("creator"),
            }
            for page_index, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                if not page_text:
                    continue
                text_parts.append(page_text)
                sections.append(
                    {
                        "title": f"Page {page_index}",
                        "page_number": page_index,
                        "content": page_text,
                    }
                )

        full_text = "\n\n".join(text_parts)
        title = raw.reference.filename.rsplit(".", 1)[0]
        if metadata.get("subject"):
            title = str(metadata["subject"])

        return ParsedDocument(
            text=full_text,
            title=title,
            metadata=metadata,
            sections=sections,
        )
