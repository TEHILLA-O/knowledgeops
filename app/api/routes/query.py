"""Query and search routes."""

from fastapi import APIRouter, Depends

from app.api.deps import QueryOrchestrator, get_query_service
from app.schemas.common import QueryRequest, QueryResponse, SearchRequest, SearchResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def run_query(
    body: QueryRequest,
    service: QueryOrchestrator = Depends(get_query_service),
) -> QueryResponse:
    return await service.query(body)


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    service: QueryOrchestrator = Depends(get_query_service),
) -> SearchResponse:
    return await service.search(body)
