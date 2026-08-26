"""HTML document parser using BeautifulSoup."""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.ingestion.parsers.base import DocumentParser
from app.schemas.common import ParsedDocument, RawDocument


class HtmlParser(DocumentParser):
    """Extract readable text and heading sections from HTML."""

    def supports(self, content_type: str, filename: str) -> bool:
        return filename.lower().endswith((".html", ".htm")) or "html" in content_type

    def parse(self, raw: RawDocument) -> ParsedDocument:
        soup = BeautifulSoup(raw.content, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else raw.reference.filename.rsplit(".", 1)[0]

        sections: list[dict[str, object]] = []
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if headings:
            for heading in headings:
                section_title = heading.get_text(" ", strip=True)
                content_parts: list[str] = []
                for sibling in heading.next_siblings:
                    if getattr(sibling, "name", None) in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                        break
                    if hasattr(sibling, "get_text"):
                        part = sibling.get_text(" ", strip=True)
                        if part:
                            content_parts.append(part)
                sections.append(
                    {
                        "title": section_title,
                        "level": heading.name,
                        "content": "\n".join(content_parts),
                    }
                )
        else:
            body_text = soup.get_text("\n", strip=True)
            if body_text:
                sections.append({"title": title, "content": body_text})

        full_text = soup.get_text("\n", strip=True)
        metadata = {
            "format": "html",
            "section_count": len(sections),
            "source_url": raw.reference.source_url,
        }
        return ParsedDocument(
            text=full_text,
            title=title,
            metadata=metadata,
            sections=sections,
        )
