"""Sparse BM25 retrieval with Qdrant payload index."""

import re
from typing import Any

from rank_bm25 import BM25Okapi

from app.core.logging import get_logger
from app.retrieval.dense import _payload_to_chunk, filters_to_qdrant_dict
from app.retrieval.qdrant_client import QdrantService
from app.schemas.common import RetrievalFilters, RetrievedChunk

logger = get_logger(__name__)

_TOKEN_PATTERN = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_PATTERN.findall(text)]


def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    max_score = max(scores)
    min_score = min(scores)
    if max_score == min_score:
        return [1.0 if max_score > 0 else 0.0 for _ in scores]
    span = max_score - min_score
    return [(s - min_score) / span for s in scores]


def _matches_filters(payload: dict[str, Any], filters: RetrievalFilters | None) -> bool:
    if not filters:
        return True
    qdrant_filters = filters_to_qdrant_dict(filters)
    for key, expected in qdrant_filters.items():
        if key == "tags":
            tags = payload.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            if expected not in tags:
                return False
        else:
            if payload.get(key) != expected:
                return False
    return True


class SparseRetriever:
    """BM25 sparse retrieval over indexed chunk payloads."""

    def __init__(self, qdrant: QdrantService) -> None:
        self.qdrant = qdrant
        self._payloads: list[dict[str, Any]] = []
        self._corpus_tokens: list[list[str]] = []
        self._bm25: BM25Okapi | None = None
        self._index_built = False

    async def build_index(self, force: bool = False) -> None:
        if self._index_built and not force:
            return
        payloads = await self.qdrant.scroll_all_payloads()
        self._payloads = [p for p in payloads if p.get("content")]
        self._corpus_tokens = [tokenize(str(p.get("content", ""))) for p in self._payloads]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None
        self._index_built = True
        logger.info("sparse_index_built", chunks=len(self._payloads))

    def build_index_from_payloads(self, payloads: list[dict[str, Any]]) -> None:
        """Build BM25 index from an in-memory payload cache."""
        self._payloads = [p for p in payloads if p.get("content")]
        self._corpus_tokens = [tokenize(str(p.get("content", ""))) for p in self._payloads]
        self._bm25 = BM25Okapi(self._corpus_tokens) if self._corpus_tokens else None
        self._index_built = True

    async def search(
        self,
        query: str,
        top_k: int = 20,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        await self.build_index()
        if not self._bm25 or not self._payloads:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        raw_scores = self._bm25.get_scores(query_tokens)
        scored_indices = [
            (idx, float(raw_scores[idx]))
            for idx in range(len(self._payloads))
            if raw_scores[idx] > 0 and _matches_filters(self._payloads[idx], filters)
        ]
        scored_indices.sort(key=lambda item: item[1], reverse=True)
        top_indices = scored_indices[:top_k]

        normalized = _normalize_scores([score for _, score in top_indices])
        chunks: list[RetrievedChunk] = []
        for (idx, _), norm_score in zip(top_indices, normalized, strict=True):
            chunk = _payload_to_chunk(self._payloads[idx], dense_score=None)
            chunk.sparse_score = norm_score
            chunks.append(chunk)

        logger.debug("sparse_retrieval_complete", query_len=len(query), results=len(chunks))
        return chunks

    def invalidate_cache(self) -> None:
        self._index_built = False
        self._payloads = []
        self._corpus_tokens = []
        self._bm25 = None
