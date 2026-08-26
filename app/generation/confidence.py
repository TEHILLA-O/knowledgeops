"""Transparent confidence scoring from retrieval and generation signals."""

from app.core.config import Settings, get_settings
from app.core.constants import ConfidenceLevel
from app.generation.grounding import grounding_score
from app.schemas.common import ConfidenceInfo, GenerationResult, RetrievedChunk


class ConfidenceScorer:
    """Derives confidence levels from retrieval, rerank, and grounding signals."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        cfg = self.settings.retrieval_config.get("confidence", {})
        self.high_threshold = float(cfg.get("high_threshold", 0.75))
        self.medium_threshold = float(cfg.get("medium_threshold", 0.5))
        self.insufficient_threshold = float(cfg.get("insufficient_threshold", 0.35))

    def score(
        self,
        chunks: list[RetrievedChunk],
        generation: GenerationResult,
        grounding: float | None = None,
    ) -> ConfidenceInfo:
        retrieval_signal = self._retrieval_signal(chunks)
        rerank_signal = self._rerank_signal(chunks)
        grounding_signal = grounding if grounding is not None else grounding_score(generation.answer, chunks)
        agreement_signal = 1.0 - (1.0 - retrieval_signal) * (1.0 - grounding_signal)

        if generation.knowledge_gap:
            composite = self.insufficient_threshold * 0.5
        else:
            composite = (
                0.35 * retrieval_signal
                + 0.35 * rerank_signal
                + 0.20 * grounding_signal
                + 0.10 * agreement_signal
            )
            composite = max(composite, generation.confidence_score * 0.25)

        level = self._level_for_score(composite, generation.knowledge_gap)
        return ConfidenceInfo(
            level=level,
            score=round(composite, 4),
            signals={
                "retrieval": round(retrieval_signal, 4),
                "rerank": round(rerank_signal, 4),
                "grounding": round(grounding_signal, 4),
                "agreement": round(agreement_signal, 4),
                "generation": round(generation.confidence_score, 4),
            },
        )

    @staticmethod
    def _retrieval_signal(chunks: list[RetrievedChunk]) -> float:
        if not chunks:
            return 0.0
        scores = [
            c.rerank_score or c.fusion_score or c.dense_score or c.sparse_score or 0.0 for c in chunks
        ]
        return max(scores)

    @staticmethod
    def _rerank_signal(chunks: list[RetrievedChunk]) -> float:
        if not chunks:
            return 0.0
        rerank_scores = [c.rerank_score for c in chunks if c.rerank_score is not None]
        if rerank_scores:
            return max(rerank_scores)
        fusion_scores = [c.fusion_score or 0.0 for c in chunks]
        return max(fusion_scores) if fusion_scores else 0.0

    def _level_for_score(self, score: float, knowledge_gap: bool) -> ConfidenceLevel:
        if knowledge_gap or score < self.insufficient_threshold:
            return ConfidenceLevel.INSUFFICIENT_EVIDENCE
        if score >= self.high_threshold:
            return ConfidenceLevel.HIGH
        if score >= self.medium_threshold:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
