"""Markdown document parser."""

from __future__ import annotations

import re

import markdown

from app.ingestion.parsers.base import DocumentParser
from app.schemas.common import ParsedDocument, RawDocument


class MarkdownParser(DocumentParser):
    """Parse markdown files into text and heading-based sections."""

    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def supports(self, content_type: str, filename: str) -> bool:
        return filename.lower().endswith((".md", ".markdown")) or content_type in {
            "text/markdown",
            "text/x-markdown",
        }

    def parse(self, raw: RawDocument) -> ParsedDocument:
        text = raw.content.decode("utf-8", errors="replace")
        sections = self._extract_sections(text)
        html = markdown.markdown(text)
        title = self._extract_title(text, raw.reference.filename)
        metadata = {
            "format": "markdown",
            "section_count": len(sections),
            "html_preview": html[:500],
        }
        return ParsedDocument(
            text=text,
            title=title,
            metadata=metadata,
            sections=sections,
        )

    def _extract_title(self, text: str, filename: str) -> str:
        match = self.HEADING_PATTERN.search(text)
        if match:
            return match.group(2).strip()
        return filename.rsplit(".", 1)[0]

    def _extract_sections(self, text: str) -> list[dict[str, object]]:
        sections: list[dict[str, object]] = []
        matches = list(self.HEADING_PATTERN.finditer(text))
        if not matches:
            stripped = text.strip()
            if stripped:
                sections.append({"title": "Content", "content": stripped})
            return sections

        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections.append(
                {
                    "title": match.group(2).strip(),
                    "level": len(match.group(1)),
                    "content": content,
                }
            )
        return sections
