"""Tests for citation building."""

from app.generation.citations import CitationBuilder
from app.schemas.common import RetrievedChunk


def _chunk(chunk_id: str, title: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        document_title=title,
        document_version=1,
        content="Policy content about vacation days.",
        section="Policies",
        page_number=1,
    )


def test_build_citations_from_chunks() -> None:
    builder = CitationBuilder()
    chunks = [_chunk("c1", "HR Handbook"), _chunk("c2", "Leave Policy")]
    citations = builder.build(chunks)
    assert len(citations) == 2
    assert citations[0].document_title == "HR Handbook"


def test_build_citations_respects_inline_references() -> None:
    builder = CitationBuilder()
    chunks = [_chunk("c1", "Doc A"), _chunk("c2", "Doc B")]
    answer = "According to policy [1], employees get vacation."
    citations = builder.build(chunks, answer)
    assert len(citations) == 1
    assert citations[0].document_title == "Doc A"


def test_format_inline() -> None:
    builder = CitationBuilder()
    chunks = [_chunk("c1", "HR Handbook")]
    citations = builder.build(chunks)
    formatted = builder.format_inline(citations)
    assert "[1]" in formatted
    assert "HR Handbook" in formatted
