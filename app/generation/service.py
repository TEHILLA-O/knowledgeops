"""Query generation service orchestrating the full RAG pipeline."""

import time

from app.core.config import Settings, get_settings
from app.core.constants import ConfidenceLevel, QueryStatus
from app.core.logging import get_logger
from app.generation.citations import CitationBuilder
from app.generation.confidence import ConfidenceScorer
from app.generation.grounding import grounding_score, is_answer_grounded
from app.generation.prompts import build_system_prompt, build_user_prompt
from app.providers.base import GenerationProvider
from app.providers.factory import create_generation_provider
from app.retrieval.service import RetrievalService
from app.schemas.common import GenerationResult, QueryRequest, QueryResponse, RetrievalFilters

logger = get_logger(__name__)


class QueryService:
    """Handles end-to-end query: retrieval, generation, grounding, citations, confidence."""

    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        generation_provider: GenerationProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.retrieval = retrieval_service or RetrievalService(settings=self.settings)
        self.generator = generation_provider or create_generation_provider(self.settings)
        self.citations = CitationBuilder()
        self.confidence_scorer = ConfidenceScorer(self.settings)
        self._retrieval_cfg = self.settings.retrieval_config.get("retrieval", {})

    async def query(self, request: QueryRequest) -> QueryResponse:
        start = time.perf_counter()
        user_group = request.user_group or self.settings.default_user_group
        filters = request.filters or RetrievalFilters()

        context_text, chunks, retrieval_debug = await self.retrieval.build_context(
            request.query,
            filters=filters,
            user_group=user_group,
        )

        min_confidence = float(self._retrieval_cfg.get("min_confidence_score", 0.35))
        best_score = self.confidence_scorer._retrieval_signal(chunks)

        if not chunks or best_score < min_confidence:
            latency_ms = int((time.perf_counter() - start) * 1000)
            gap_result = GenerationResult(
                answer="",
                confidence_score=best_score,
                confidence_level=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
                knowledge_gap=True,
            )
            return QueryResponse(
                query=request.query,
                answer="I do not have sufficient evidence in the knowledge base to answer this question.",
                status=QueryStatus.INSUFFICIENT_EVIDENCE,
                confidence=self.confidence_scorer.score(chunks, gap_result),
                citations=[],
                retrieval=retrieval_debug,
                latency_ms=latency_ms,
                debug=retrieval_debug if request.include_debug else None,
            )

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(request.query, context_text)
        generation = await self.generator.generate(system_prompt, user_prompt)

        ground = grounding_score(generation.answer, chunks)
        if not is_answer_grounded(generation.answer, chunks):
            generation.knowledge_gap = True
            if generation.confidence_level != ConfidenceLevel.INSUFFICIENT_EVIDENCE:
                generation.confidence_level = ConfidenceLevel.LOW

        confidence = self.confidence_scorer.score(chunks, generation, grounding=ground)
        citation_list = self.citations.build(chunks, generation.answer)

        if confidence.level == ConfidenceLevel.INSUFFICIENT_EVIDENCE or generation.knowledge_gap:
            status = QueryStatus.INSUFFICIENT_EVIDENCE
        else:
            status = QueryStatus.ANSWERED

        latency_ms = int((time.perf_counter() - start) * 1000)
        debug = None
        if request.include_debug:
            debug = {
                **retrieval_debug,
                "grounding_score": ground,
                "generation_provider": self.generator.provider_name,
                "chunks": [c.model_dump() for c in chunks],
            }

        logger.info(
            "query_complete",
            status=status.value,
            confidence=confidence.level.value,
            latency_ms=latency_ms,
        )

        return QueryResponse(
            query=request.query,
            answer=generation.answer,
            status=status,
            confidence=confidence,
            citations=citation_list,
            retrieval=retrieval_debug,
            latency_ms=latency_ms,
            debug=debug,
        )
