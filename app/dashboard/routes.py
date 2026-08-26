"""Server-rendered Jinja2 dashboard routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import QueryOrchestrator, Repositories, get_query_service, get_repositories
from app.schemas.common import AnalyticsSummary

TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _build_analytics(repos: Repositories) -> AnalyticsSummary:
    docs = await repos.analytics.documents_indexed_count()
    chunks = await repos.analytics.chunks_indexed_count()
    queries_today = await repos.analytics.queries_today_count()
    breakdown = await repos.analytics.query_status_breakdown(days=1)
    total_today = sum(breakdown.values()) or 1
    answered = breakdown.get("ANSWERED", 0)
    insufficient = breakdown.get("INSUFFICIENT_EVIDENCE", 0)
    avg_latency = await repos.analytics.avg_retrieval_latency_ms(days=7)
    gaps = await repos.analytics.knowledge_gaps_count()
    latest_score = await repos.evaluations.get_latest_score()
    index_health = await repos.analytics.latest_ingestion_health()
    return AnalyticsSummary(
        documents_indexed=docs,
        chunks_indexed=chunks,
        queries_today=queries_today,
        answered_percentage=round(answered / total_today * 100, 2),
        insufficient_evidence_percentage=round(insufficient / total_today * 100, 2),
        average_retrieval_latency_ms=round(avg_latency, 2),
        knowledge_gaps_count=gaps,
        latest_evaluation_score=latest_score,
        index_health=index_health,
    )


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_home(
    request: Request,
    repos: Repositories = Depends(get_repositories),
) -> HTMLResponse:
    analytics = await _build_analytics(repos)
    recent_queries, _ = await repos.queries.list_queries(page=1, page_size=10)
    knowledge_gaps, _ = await repos.knowledge_gaps.list_gaps(page=1, page_size=10, status="UNRESOLVED")
    ingestion_runs, _ = await repos.ingestion.list_runs(page=1, page_size=5)
    documents, _ = await repos.documents.list_documents(page=1, page_size=10)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active": "dashboard",
            "analytics": analytics,
            "recent_queries": recent_queries,
            "knowledge_gaps": knowledge_gaps,
            "ingestion_runs": ingestion_runs,
            "documents": documents,
        },
    )


@router.get("/debug", response_class=HTMLResponse)
async def debug_page(
    request: Request,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "debug.html",
        {"active": "debug", "results": None, "query_text": "", "top_k": 10},
    )


@router.post("/debug", response_class=HTMLResponse)
async def debug_search(
    request: Request,
    query: str = Form(...),
    top_k: int = Form(default=10),
    service: QueryOrchestrator = Depends(get_query_service),
) -> HTMLResponse:
    error = None
    results = None
    latency_ms = 0
    try:
        from app.schemas.common import SearchRequest

        response = await service.search(SearchRequest(query=query, top_k=top_k))
        results = response.results
        latency_ms = response.latency_ms
    except Exception as exc:
        error = str(exc)

    return templates.TemplateResponse(
        request,
        "debug.html",
        {
            "active": "debug",
            "query_text": query,
            "top_k": top_k,
            "results": results,
            "latency_ms": latency_ms,
            "error": error,
        },
    )


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def document_detail(
    request: Request,
    document_id: str,
    repos: Repositories = Depends(get_repositories),
) -> HTMLResponse:
    document = await repos.documents.get_by_id(document_id)
    versions = await repos.documents.get_versions(document_id)
    chunks = [c for c in document.chunks if c.is_active][:50]

    return templates.TemplateResponse(
        request,
        "document.html",
        {
            "active": "dashboard",
            "document": document,
            "versions": versions,
            "chunks": chunks,
        },
    )
