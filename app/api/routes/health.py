"""Health check routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_qdrant
from app.core.config import get_settings
from app.db.session import get_db
from app.retrieval.qdrant_client import QdrantService
from app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(
    db: AsyncSession = Depends(get_db),
    qdrant: QdrantService = Depends(get_qdrant),
) -> ReadinessResponse:
    postgres_status = "down"
    qdrant_status = "down"

    try:
        await db.execute(text("SELECT 1"))
        postgres_status = "up"
    except Exception:
        postgres_status = "down"

    try:
        qdrant_status = "up" if await qdrant.health_check() else "down"
    except Exception:
        qdrant_status = "down"

    overall = "ready" if postgres_status == "up" and qdrant_status == "up" else "not_ready"
    return ReadinessResponse(status=overall, postgres=postgres_status, qdrant=qdrant_status)
