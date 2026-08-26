"""Build context windows from retrieved chunks with deduplication and budgeting."""

import hashlib

import tiktoken

from app.core.logging import get_logger
from app.schemas.common import RetrievedChunk

logger = get_logger(__name__)

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


class ContextBuilder:
    """Assembles a token-budgeted, deduplicated context from retrieved chunks."""

    def __init__(
        self,
        max_context_tokens: int = 4000,
        context_top_k: int = 5,
        source_diversity: bool = True,
        max_chunks_per_document: int = 2,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.context_top_k = context_top_k
        self.source_diversity = source_diversity
        self.max_chunks_per_document = max_chunks_per_document

    def build(
        self,
        chunks: list[RetrievedChunk],
        include_citation_metadata: bool = True,
    ) -> tuple[str, list[RetrievedChunk]]:
        deduped = self._dedupe(chunks)
        diverse = self._apply_diversity(deduped)
        selected, context_text = self._apply_token_budget(diverse)

        if include_citation_metadata:
            for chunk in selected:
                chunk.metadata.setdefault("citation_index", selected.index(chunk) + 1)
                chunk.metadata.setdefault(
                    "citation_label",
                    self._citation_label(chunk, selected.index(chunk) + 1),
                )

        logger.debug(
            "context_built",
            input_chunks=len(chunks),
            selected=len(selected),
            tokens=count_tokens(context_text),
        )
        return context_text, selected

    def _dedupe(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        seen_ids: set[str] = set()
        seen_hashes: set[str] = set()
        result: list[RetrievedChunk] = []
        for chunk in chunks:
            if chunk.chunk_id in seen_ids:
                continue
            content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_ids.add(chunk.chunk_id)
            seen_hashes.add(content_hash)
            result.append(chunk)
        return result

    def _apply_diversity(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not self.source_diversity:
            return chunks
        per_doc: dict[str, int] = {}
        result: list[RetrievedChunk] = []
        for chunk in chunks:
            count = per_doc.get(chunk.document_id, 0)
            if count >= self.max_chunks_per_document:
                continue
            per_doc[chunk.document_id] = count + 1
            result.append(chunk)
        return result

    def _apply_token_budget(
        self,
        chunks: list[RetrievedChunk],
    ) -> tuple[list[RetrievedChunk], str]:
        selected: list[RetrievedChunk] = []
        parts: list[str] = []
        used_tokens = 0

        for chunk in chunks[: self.context_top_k]:
            block = self._format_chunk_block(chunk, len(selected) + 1)
            block_tokens = count_tokens(block)
            if used_tokens + block_tokens > self.max_context_tokens and selected:
                break
            if block_tokens > self.max_context_tokens and not selected:
                truncated = self._truncate_content(chunk.content, self.max_context_tokens - 50)
                block = self._format_chunk_block(chunk, len(selected) + 1, content_override=truncated)
                block_tokens = count_tokens(block)
            selected.append(chunk)
            parts.append(block)
            used_tokens += block_tokens

        return selected, "\n\n".join(parts)

    @staticmethod
    def _format_chunk_block(
        chunk: RetrievedChunk,
        index: int,
        content_override: str | None = None,
    ) -> str:
        content = content_override or chunk.content
        header = f"[{index}] {chunk.document_title}"
        if chunk.section:
            header += f" — {chunk.section}"
        if chunk.page_number is not None:
            header += f" (p. {chunk.page_number})"
        return f"{header}\n{content}"

    @staticmethod
    def _citation_label(chunk: RetrievedChunk, index: int) -> str:
        parts = [f"[{index}]", chunk.document_title]
        if chunk.section:
            parts.append(chunk.section)
        if chunk.page_number is not None:
            parts.append(f"p.{chunk.page_number}")
        return " — ".join(parts)

    @staticmethod
    def _truncate_content(content: str, max_tokens: int) -> str:
        tokens = _ENCODING.encode(content)
        if len(tokens) <= max_tokens:
            return content
        return _ENCODING.decode(tokens[:max_tokens]) + "..."
