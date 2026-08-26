"""Tests for confidence scoring."""

from app.core.constants import ConfidenceLevel
from app.generation.confidence import ConfidenceScorer
from app.schemas.common import GenerationResult, RetrievedChunk


def _chunk(score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        document_title="Doc",
        document_version=1,
        content="Vacation policy details for employees.",
        rerank_score=score,
    )


def test_high_confidence_with_strong_retrieval() -> None:
    scorer = ConfidenceScorer()
    generation = GenerationResult(
        answer="Employees receive 20 vacation days.",
        confidence_score=0.8,
        confidence_level=ConfidenceLevel.HIGH,
        knowledge_gap=False,
    )
    result = scorer.score([_chunk(0.9)], generation, grounding=0.8)
    assert result.level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
    assert result.score > 0.5


def test_insufficient_evidence_on_knowledge_gap() -> None:
    scorer = ConfidenceScorer()
    generation = GenerationResult(
        answer="",
        confidence_score=0.1,
        confidence_level=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
        knowledge_gap=True,
    )
    result = scorer.score([], generation)
    assert result.level == ConfidenceLevel.INSUFFICIENT_EVIDENCE


def test_retrieval_signal_empty_chunks() -> None:
    scorer = ConfidenceScorer()
    assert scorer._retrieval_signal([]) == 0.0
