"""Citation builder for retrieved chunks."""

import re

from app.schemas.common import CitationInfo, RetrievedChunk

_CITATION_REF = re.compile(r"\[(\d+)\]")


class CitationBuilder:
    """Builds structured citations from retrieved chunks and answer text."""

    def build(
        self,
        chunks: list[RetrievedChunk],
        answer: str | None = None,
    ) -> list[CitationInfo]:
        referenced_indices = self._referenced_indices(answer) if answer else set(range(1, len(chunks) + 1))
        citations: list[CitationInfo] = []

        for idx, chunk in enumerate(chunks, start=1):
            if referenced_indices and idx not in referenced_indices:
                continue
            label = chunk.metadata.get("citation_label") or chunk.document_title
            citations.append(
                CitationInfo(
                    document_id=chunk.document_id,
                    document_title=chunk.document_title,
                    version=chunk.document_version,
                    page=chunk.page_number,
                    section=chunk.section,
                    chunk_id=chunk.chunk_id,
                    source_url=chunk.source_url,
                    citation_text=str(label),
                )
            )
        return citations

    @staticmethod
    def _referenced_indices(answer: str) -> set[int]:
        return {int(match) for match in _CITATION_REF.findall(answer)}

    def format_inline(self, citations: list[CitationInfo]) -> str:
        parts: list[str] = []
        for idx, citation in enumerate(citations, start=1):
            label = citation.citation_text or citation.document_title
            parts.append(f"[{idx}] {label}")
        return "; ".join(parts)
