"""Tests for document parsers."""

from app.ingestion.parsers import MarkdownParser, TextParser, default_parser_registry
from app.schemas.common import DocumentReference, RawDocument


def test_text_parser() -> None:
    ref = DocumentReference(stable_id="t1", filename="notes.txt", source="test", checksum="abc")
    raw = RawDocument(
        reference=ref, content=b"Title line\n\nBody content here.", content_type="text/plain"
    )
    parser = TextParser()
    assert parser.supports("text/plain", "notes.txt")
    parsed = parser.parse(raw)
    assert "Body content" in parsed.text
    assert parsed.title == "Title line"


def test_markdown_parser_sections() -> None:
    ref = DocumentReference(stable_id="m1", filename="doc.md", source="test", checksum="abc")
    content = b"# Main Title\n\nIntro paragraph.\n\n## Section One\n\nSection content here."
    raw = RawDocument(reference=ref, content=content, content_type="text/markdown")
    parser = MarkdownParser()
    parsed = parser.parse(raw)
    assert parsed.title == "Main Title"
    assert len(parsed.sections) >= 1


def test_parser_registry_selects_markdown() -> None:
    ref = DocumentReference(stable_id="m2", filename="guide.md", source="test", checksum="def")
    raw = RawDocument(reference=ref, content=b"# Guide\n\nContent.", content_type="text/markdown")
    parsed = default_parser_registry.parse(raw)
    assert parsed.title == "Guide"
