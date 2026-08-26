"""Chunking strategies for document text."""

from __future__ import annotations

import re
from typing import Any

import tiktoken

from app.ingestion.hashing import chunk_content_hash
from app.schemas.common import DocumentChunk, ParsedDocument

SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens using tiktoken with a word-count fallback."""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text.split()))


def _make_chunk(
    *,
    document_id: str,
    document_stable_id: str,
    document_title: str,
    document_version: int,
    chunk_index: int,
    content: str,
    section: str | None = None,
    page_number: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_content_hash(document_stable_id, chunk_index, content),
        document_id=document_id,
        document_stable_id=document_stable_id,
        document_title=document_title,
        document_version=document_version,
        chunk_index=chunk_index,
        content=content,
        content_hash=chunk_content_hash(document_stable_id, chunk_index, content),
        section=section,
        page_number=page_number,
        token_count=count_tokens(content),
        metadata=metadata or {},
    )


def fixed_chunk(
    text: str,
    *,
    document_id: str,
    document_stable_id: str,
    document_title: str,
    document_version: int,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    min_chunk_length: int = 100,
) -> list[DocumentChunk]:
    """Split text into fixed-size character chunks with overlap."""
    if not text.strip():
        return []

    chunks: list[DocumentChunk] = []
    start = 0
    chunk_index = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        content = text[start:end].strip()
        if len(content) >= min_chunk_length or end >= text_length:
            chunks.append(
                _make_chunk(
                    document_id=document_id,
                    document_stable_id=document_stable_id,
                    document_title=document_title,
                    document_version=document_version,
                    chunk_index=chunk_index,
                    content=content,
                )
            )
            chunk_index += 1
        if end >= text_length:
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


def sentence_aware_chunk(
    text: str,
    *,
    document_id: str,
    document_stable_id: str,
    document_title: str,
    document_version: int,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    min_chunk_length: int = 100,
) -> list[DocumentChunk]:
    """Group sentences into chunks that respect approximate token limits."""
    sentences = [part.strip() for part in SENTENCE_PATTERN.split(text) if part.strip()]
    if not sentences:
        return []

    chunks: list[DocumentChunk] = []
    current_sentences: list[str] = []
    current_length = 0
    chunk_index = 0

    def flush() -> None:
        nonlocal chunk_index, current_sentences, current_length
        if not current_sentences:
            return
        content = " ".join(current_sentences).strip()
        if len(content) >= min_chunk_length or not chunks:
            chunks.append(
                _make_chunk(
                    document_id=document_id,
                    document_stable_id=document_stable_id,
                    document_title=document_title,
                    document_version=document_version,
                    chunk_index=chunk_index,
                    content=content,
                )
            )
            chunk_index += 1
        current_sentences = []
        current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)
        if current_sentences and current_length + sentence_length + 1 > chunk_size:
            flush()
            if chunk_overlap > 0 and chunks:
                overlap_text = chunks[-1].content[-chunk_overlap:]
                current_sentences = [overlap_text]
                current_length = len(overlap_text)
        current_sentences.append(sentence)
        current_length += sentence_length + 1

    flush()
    return chunks


def section_aware_chunk(
    parsed: ParsedDocument,
    *,
    document_id: str,
    document_stable_id: str,
    document_version: int,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    min_chunk_length: int = 100,
    preserve_headings: bool = True,
) -> list[DocumentChunk]:
    """Chunk by document sections, falling back to sentence-aware chunking."""
    chunks: list[DocumentChunk] = []
    chunk_index = 0

    if not parsed.sections:
        return sentence_aware_chunk(
            parsed.text,
            document_id=document_id,
            document_stable_id=document_stable_id,
            document_title=parsed.title,
            document_version=document_version,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )

    for section in parsed.sections:
        section_title = str(section.get("title", "Section"))
        section_content = str(section.get("content", "")).strip()
        page_number = section.get("page_number")
        if not section_content:
            continue

        if preserve_headings:
            section_content = f"{section_title}\n\n{section_content}"

        section_chunks = sentence_aware_chunk(
            section_content,
            document_id=document_id,
            document_stable_id=document_stable_id,
            document_title=parsed.title,
            document_version=document_version,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )

        for section_chunk in section_chunks:
            chunks.append(
                _make_chunk(
                    document_id=document_id,
                    document_stable_id=document_stable_id,
                    document_title=parsed.title,
                    document_version=document_version,
                    chunk_index=chunk_index,
                    content=section_chunk.content,
                    section=section_title,
                    page_number=int(page_number) if isinstance(page_number, int) else None,
                    metadata={"section_title": section_title},
                )
            )
            chunk_index += 1

    return chunks


def chunk_document(
    parsed: ParsedDocument,
    *,
    document_id: str,
    document_stable_id: str,
    document_version: int,
    strategy: str = "sentence_aware",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    min_chunk_length: int = 100,
    preserve_headings: bool = True,
) -> list[DocumentChunk]:
    """Apply the configured chunking strategy to a parsed document."""
    if strategy == "fixed":
        return fixed_chunk(
            parsed.text,
            document_id=document_id,
            document_stable_id=document_stable_id,
            document_title=parsed.title,
            document_version=document_version,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
    if strategy == "section_aware":
        return section_aware_chunk(
            parsed,
            document_id=document_id,
            document_stable_id=document_stable_id,
            document_version=document_version,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
            preserve_headings=preserve_headings,
        )
    return sentence_aware_chunk(
        parsed.text,
        document_id=document_id,
        document_stable_id=document_stable_id,
        document_title=parsed.title,
        document_version=document_version,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_length=min_chunk_length,
    )
