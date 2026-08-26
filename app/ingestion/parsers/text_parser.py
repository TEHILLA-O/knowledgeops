"""Plain text document parser."""

from __future__ import annotations

from app.ingestion.parsers.base import DocumentParser
from app.schemas.common import ParsedDocument, RawDocument


class TextParser(DocumentParser):
    """Parse plain text files."""

    def supports(self, content_type: str, filename: str) -> bool:
        return filename.lower().endswith(".txt") or content_type.startswith("text/")

    def parse(self, raw: RawDocument) -> ParsedDocument:
        text = raw.content.decode("utf-8", errors="replace")
        title = raw.reference.filename.rsplit(".", 1)[0]
        first_line = text.strip().splitlines()[0] if text.strip() else title
        if len(first_line) <= 120:
            title = first_line
        return ParsedDocument(
            text=text,
            title=title,
            metadata={"format": "text", "line_count": len(text.splitlines())},
            sections=[{"title": title, "content": text.strip()}] if text.strip() else [],
        )
