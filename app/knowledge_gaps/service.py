"""Knowledge gap detection and clustering service."""

import re
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import numpy as np

from app.core.config import Settings, get_settings
from app.core.constants import ConfidenceLevel
from app.db.models import KnowledgeGap, generate_uuid
from app.repositories.knowledge_gap_repo import KnowledgeGapRepository


def normalize_question(text: str) -> str:
    """Normalize question text for deduplication."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


@lru_cache(maxsize=1)
def _get_embedding_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class KnowledgeGapService:
    SIMILARITY_THRESHOLD = 0.85

    def __init__(
        self,
        repo: KnowledgeGapRepository,
        settings: Settings | None = None,
    ) -> None:
        self.repo = repo
        self.settings = settings or get_settings()

    def _embed(self, texts: list[str]) -> np.ndarray:
        model = _get_embedding_model(self.settings.embedding_model)
        vectors = model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)

    async def record_from_query(
        self,
        question: str,
        *,
        confidence_level: ConfidenceLevel | str,
        confidence_score: float,
        best_retrieval_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeGap | None:
        """Create or update a knowledge gap when confidence is low."""
        level = (
            confidence_level
            if isinstance(confidence_level, ConfidenceLevel)
            else ConfidenceLevel(str(confidence_level))
        )
        if level not in (ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT_EVIDENCE):
            return None

        normalized = normalize_question(question)
        existing = await self.repo.find_by_normalized_question(normalized)
        if existing:
            existing.frequency += 1
            existing.best_retrieval_score = best_retrieval_score
            existing.last_seen_at = datetime.now(UTC)
            if metadata:
                existing.metadata_json = {**(existing.metadata_json or {}), **metadata}
            return await self.repo.update(existing)

        cluster_id = await self._find_similar_cluster(question)
        gap = KnowledgeGap(
            id=generate_uuid(),
            question=question,
            normalized_question=normalized,
            cluster_id=cluster_id,
            suggested_topic=self._suggest_topic(question),
            frequency=1,
            best_retrieval_score=best_retrieval_score,
            status="UNRESOLVED",
            metadata_json=metadata or {},
        )
        return await self.repo.create(gap)

    async def _find_similar_cluster(self, question: str) -> str | None:
        """Cluster similar questions using embedding cosine similarity."""
        unresolved = await self.repo.list_unresolved()
        if not unresolved:
            return generate_uuid()

        candidates = [g.question for g in unresolved]
        vectors = self._embed([question, *candidates])
        query_vec = vectors[0]
        candidate_vecs = vectors[1:]

        similarities = candidate_vecs @ query_vec
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        if best_score >= self.SIMILARITY_THRESHOLD:
            matched = unresolved[best_idx]
            return matched.cluster_id or matched.id
        return generate_uuid()

    @staticmethod
    def _suggest_topic(question: str) -> str:
        words = [w for w in normalize_question(question).split() if len(w) > 3]
        return " ".join(words[:5]) if words else question[:80]

    async def recluster_all(self) -> int:
        """Re-cluster all unresolved gaps. Returns number of clusters."""
        gaps = await self.repo.list_unresolved()
        if len(gaps) < 2:
            return len(gaps)

        questions = [g.question for g in gaps]
        vectors = self._embed(questions)
        assigned: dict[str, str] = {}
        cluster_count = 0

        for i, gap in enumerate(gaps):
            if gap.id in assigned:
                continue
            cluster_id = generate_uuid()
            cluster_count += 1
            assigned[gap.id] = cluster_id
            gap.cluster_id = cluster_id

            for j in range(i + 1, len(gaps)):
                other = gaps[j]
                if other.id in assigned:
                    continue
                sim = float(vectors[i] @ vectors[j])
                if sim >= self.SIMILARITY_THRESHOLD:
                    assigned[other.id] = cluster_id
                    other.cluster_id = cluster_id

        for gap in gaps:
            await self.repo.update(gap)
        return cluster_count
