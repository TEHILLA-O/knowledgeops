"""Tests for chunking strategies."""

from app.ingestion.chunking.strategies import (
    chunk_document,
    count_tokens,
    fixed_chunk,
    sentence_aware_chunk,
)
from app.schemas.common import ParsedDocument


def test_count_tokens_positive() -> None:
    assert count_tokens("hello world test") >= 1


def test_fixed_chunk_respects_size() -> None:
    text = "word " * 200
    chunks = fixed_chunk(
        text,
        document_id="doc-1",
        document_stable_id="stable-1",
        document_title="Title",
        document_version=1,
        chunk_size=100,
        chunk_overlap=10,
        min_chunk_length=20,
    )
    assert len(chunks) >= 2
    assert all(c.chunk_index == i for i, c in enumerate(chunks))


def test_sentence_aware_chunk() -> None:
    text = "First sentence here. Second sentence follows. Third sentence ends."
    chunks = sentence_aware_chunk(
        text,
        document_id="doc-1",
        document_stable_id="stable-1",
        document_title="Title",
        document_version=1,
        chunk_size=80,
        min_chunk_length=10,
    )
    assert len(chunks) >= 1
    assert "sentence" in chunks[0].content.lower()


def test_chunk_document_section_aware() -> None:
    parsed = ParsedDocument(
        text="Full text",
        title="Doc",
        sections=[
            {"title": "Section A", "content": "Content for section A with enough words."},
            {"title": "Section B", "content": "Content for section B with enough words."},
        ],
    )
    chunks = chunk_document(
        parsed,
        document_id="doc-1",
        document_stable_id="stable-1",
        document_version=1,
        strategy="section_aware",
        min_chunk_length=10,
    )
    assert len(chunks) >= 1
    assert any(c.section == "Section A" for c in chunks)
