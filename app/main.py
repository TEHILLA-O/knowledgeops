"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import (
    analytics,
    documents,
    evaluations,
    health,
    ingestion,
    knowledge_gaps,
    query,
)
from app.core.config import get_settings
from app.core.exceptions import KnowledgeOpsError
from app.core.logging import get_logger, setup_logging
from app.dashboard.routes import router as dashboard_router
from app.db.session import init_db
from app.retrieval.qdrant_client import QdrantService

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("application_starting", app=settings.app_name)
    await init_db()
    qdrant = QdrantService(settings)
    await qdrant.ensure_collection()
    app.state.qdrant = qdrant
    yield
    logger.info("application_stopping")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(query.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(knowledge_gaps.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(dashboard_router)


@app.exception_handler(KnowledgeOpsError)
async def knowledgeops_exception_handler(
    request: Request, exc: KnowledgeOpsError
) -> JSONResponse:
    status_code = 404 if exc.code == "NOT_FOUND" else 400
    if exc.code == "INTERNAL_ERROR":
        status_code = 500
    return JSONResponse(
        status_code=status_code,
        content={"error": exc.message, "code": exc.code},
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "KnowledgeOps RAG Automation Platform", "docs": "/docs"}
