"""FastAPI dependency injection."""

from typing import Any, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import ConfidenceLevel, QueryStatus
from app.db.models import (
    Answer,
    Citation,
    QueryRecord,
    QueryRetrieval,
    generate_uuid,
)
from app.db.session import get_db
from app.evaluation.runner import EvaluationRunner
from app.generation.service import QueryService as GenerationQueryService
from app.knowledge_gaps.service import KnowledgeGapService
from app.providers.factory import create_embedding_provider
from app.repositories import (
    AnalyticsRepository,
    DocumentRepository,
    EvaluationRepository,
    IngestionRepository,
    KnowledgeGapRepository,
    QueryRepository,
)
from app.retrieval.qdrant_client import QdrantService
from app.retrieval.service import RetrievalService
from app.schemas.common import (
    IngestionRunSummary,
    QueryRequest,
    QueryResponse,
    RetrievalFilters,
    SearchRequest,
    SearchResponse,
)


class Repositories:
    def __init__(self, session: AsyncSession) -> None:
        self.documents = DocumentRepository(session)
        self.ingestion = IngestionRepository(session)
        self.queries = QueryRepository(session)
        self.knowledge_gaps = KnowledgeGapRepository(session)
        self.evaluations = EvaluationRepository(session)
        self.analytics = AnalyticsRepository(session)


class QueryOrchestrator:
    """Wraps generation QueryService with persistence and knowledge gap tracking."""

    def __init__(
        self,
        repos: Repositories,
        generation_service: GenerationQueryService,
        retrieval_service: RetrievalService,
        gap_service: KnowledgeGapService,
    ) -> None:
        self.repos = repos
        self.generation = generation_service
        self.retrieval = retrieval_service
        self.gap_service = gap_service

    async def query(self, request: QueryRequest) -> QueryResponse:
        response = await self.generation.query(request)
        await self._persist_query(request, response)
        if response.status == QueryStatus.INSUFFICIENT_EVIDENCE or (
            response.confidence
            and response.confidence.level
            in (ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT_EVIDENCE)
        ):
            best_score = response.confidence.score if response.confidence else None
            await self.gap_service.record_from_query(
                request.query,
                confidence_level=response.confidence.level if response.confidence else ConfidenceLevel.LOW,
                confidence_score=best_score or 0.0,
                best_retrieval_score=best_score,
                metadata={"status": response.status.value},
            )
        return response

    async def search(self, request: SearchRequest) -> SearchResponse:
        filters = request.filters or RetrievalFilters()
        chunks, debug = await self.retrieval.search(
            request.query,
            filters=filters,
            user_group=request.user_group,
            top_k=request.top_k,
        )
        return SearchResponse(
            query=request.query,
            results=chunks,
            latency_ms=int(debug.get("latency_ms", 0)),
        )

    async def _persist_query(self, request: QueryRequest, response: QueryResponse) -> None:
        record = QueryRecord(
            id=generate_uuid(),
            query_text=request.query,
            user_group=request.user_group,
            status=response.status.value,
            retrieval_latency_ms=int(response.retrieval.get("latency_ms", 0)),
            total_latency_ms=response.latency_ms,
            metadata_json={"include_debug": request.include_debug},
        )
        await self.repos.queries.create_query(record)

        debug_chunks = (response.debug or {}).get("chunks", [])
        retrievals: list[QueryRetrieval] = []
        for rank, chunk_data in enumerate(debug_chunks, start=1):
            if isinstance(chunk_data, dict):
                chunk_id = chunk_data.get("chunk_id", "")
                retrievals.append(
                    QueryRetrieval(
                        id=generate_uuid(),
                        query_id=record.id,
                        chunk_id=chunk_id,
                        dense_score=chunk_data.get("dense_score"),
                        sparse_score=chunk_data.get("sparse_score"),
                        fusion_score=chunk_data.get("fusion_score"),
                        rerank_score=chunk_data.get("rerank_score"),
                        rank=rank,
                        used_in_context=rank <= 5,
                    )
                )
        if retrievals:
            await self.repos.queries.add_retrievals(retrievals)

        if response.answer and response.confidence:
            answer = Answer(
                id=generate_uuid(),
                query_id=record.id,
                answer_text=response.answer,
                confidence_level=response.confidence.level.value,
                confidence_score=response.confidence.score,
                knowledge_gap=response.status == QueryStatus.INSUFFICIENT_EVIDENCE,
            )
            citations = [
                Citation(
                    id=generate_uuid(),
                    answer_id=answer.id,
                    document_id=c.document_id,
                    document_title=c.document_title,
                    chunk_id=c.chunk_id,
                    version=c.version,
                    page=c.page,
                    section=c.section,
                    source_url=c.source_url,
                )
                for c in response.citations
            ]
            await self.repos.queries.save_answer(answer, citations)


class IngestionService:
    """Triggers ingestion pipeline runs."""

    def __init__(
        self,
        session: AsyncSession,
        qdrant: QdrantService,
        settings: Settings,
    ) -> None:
        self.session = session
        self.qdrant = qdrant
        self.settings = settings

    async def run(self, source: str = "demo") -> IngestionRunSummary:
        from app.ingestion.discovery.base import DocumentSource
        from app.ingestion.discovery.demo import DemoSource
        from app.ingestion.pipeline import IngestionPipeline

        embedding = create_embedding_provider(self.settings)
        pipeline = IngestionPipeline(self.session, self.qdrant, embedding, self.settings)

        doc_source: DocumentSource
        if source == "demo":
            doc_source = DemoSource(self.settings)
        else:
            from app.ingestion.discovery.local_folder import LocalFolderSource

            cfg = self.settings.ingestion_config.get("sources", {}).get("local_folder", {})
            doc_source = LocalFolderSource(
                folder_path=cfg.get("path", "data/documents"),
                source_name=source,
                settings=self.settings,
            )
        return await pipeline.run(doc_source)


class EvaluationSearchAdapter:
    """Adapts RetrievalService for evaluation runner."""

    def __init__(self, retrieval: RetrievalService) -> None:
        self.retrieval = retrieval

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        retrieval_filters = RetrievalFilters(**filters) if filters else None
        chunks, _ = await self.retrieval.search(query, filters=retrieval_filters, top_k=top_k)
        return [c.model_dump() for c in chunks]


async def get_repositories(
    session: AsyncSession = Depends(get_db),
) -> Repositories:
    return Repositories(session)


def get_qdrant(request: Request) -> QdrantService:
    return cast(QdrantService, request.app.state.qdrant)


async def get_retrieval_service(
    qdrant: QdrantService = Depends(get_qdrant),
    settings: Settings = Depends(get_settings),
) -> RetrievalService:
    return RetrievalService(qdrant=qdrant, settings=settings)


async def get_gap_service(
    repos: Repositories = Depends(get_repositories),
    settings: Settings = Depends(get_settings),
) -> KnowledgeGapService:
    return KnowledgeGapService(repos.knowledge_gaps, settings)


async def get_query_service(
    repos: Repositories = Depends(get_repositories),
    qdrant: QdrantService = Depends(get_qdrant),
    settings: Settings = Depends(get_settings),
    gap_service: KnowledgeGapService = Depends(get_gap_service),
) -> QueryOrchestrator:
    retrieval = RetrievalService(qdrant=qdrant, settings=settings)
    generation = GenerationQueryService(retrieval_service=retrieval, settings=settings)
    return QueryOrchestrator(repos, generation, retrieval, gap_service)


async def get_ingestion_service(
    session: AsyncSession = Depends(get_db),
    qdrant: QdrantService = Depends(get_qdrant),
    settings: Settings = Depends(get_settings),
) -> IngestionService:
    return IngestionService(session, qdrant, settings)


async def get_evaluation_runner(
    repos: Repositories = Depends(get_repositories),
    qdrant: QdrantService = Depends(get_qdrant),
    settings: Settings = Depends(get_settings),
) -> EvaluationRunner:
    retrieval = RetrievalService(qdrant=qdrant, settings=settings)
    adapter = EvaluationSearchAdapter(retrieval)
    return EvaluationRunner(repos.evaluations, adapter, settings)
