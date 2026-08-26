"""Shared pytest fixtures with in-memory DB, mock Qdrant, and mock embeddings."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from qdrant_client.http import models as qmodels
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure test environment before app imports read settings
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("GENERATION_PROVIDER", "mock")
os.environ.setdefault("RERANKING_PROVIDER", "none")
os.environ.setdefault("APP_ENV", "test")

from app.core.config import Settings, get_settings
from app.db.models import Base
from app.main import app
from app.providers.mock_embedding import MockEmbeddingProvider
from app.retrieval.qdrant_client import QdrantService


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class MockQdrantPoint:
    point_id: str
    vector: list[float]
    payload: dict[str, Any]


class MockQdrantService:
    """In-memory Qdrant substitute for unit and integration tests."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.collection = self.settings.qdrant_collection
        self._points: dict[str, MockQdrantPoint] = {}
        self._vector_size = 384

    @staticmethod
    def point_id_from_chunk(chunk_id: str) -> str:
        return QdrantService.point_id_from_chunk(chunk_id)

    async def ensure_collection(self, vector_size: int = 384) -> None:
        self._vector_size = vector_size

    async def upsert_vectors(self, points: list[dict[str, Any]]) -> None:
        for point in points:
            self._points[point["point_id"]] = MockQdrantPoint(
                point_id=point["point_id"],
                vector=point["vector"],
                payload=point["payload"],
            )

    async def delete_by_document_id(self, document_id: str) -> None:
        to_delete = [
            pid for pid, p in self._points.items() if p.payload.get("document_id") == document_id
        ]
        for pid in to_delete:
            del self._points[pid]

    async def delete_by_point_ids(self, point_ids: list[str]) -> None:
        for pid in point_ids:
            self._points.pop(pid, None)

    async def search_dense(
        self,
        vector: list[float],
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[qmodels.ScoredPoint]:
        scored: list[tuple[float, MockQdrantPoint]] = []
        for point in self._points.values():
            if filters and not self._matches_filters(point.payload, filters):
                continue
            score = _cosine_similarity(vector, point.vector)
            scored.append((score, point))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[qmodels.ScoredPoint] = []
        for score, point in scored[:limit]:
            results.append(
                qmodels.ScoredPoint(
                    id=point.point_id,
                    version=1,
                    score=score,
                    payload=point.payload,
                    vector=None,
                )
            )
        return results

    async def scroll_all_payloads(self) -> list[dict[str, Any]]:
        return [dict(p.payload) for p in self._points.values()]

    async def count_points(self) -> int:
        return len(self._points)

    async def health_check(self) -> bool:
        return True

    def _matches_filters(self, payload: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, value in filters.items():
            if value is None:
                continue
            if key == "allowed_groups":
                allowed = payload.get("allowed_groups") or []
                expected = value if isinstance(value, list) else [value]
                if not any(group in allowed for group in expected):
                    return False
            elif payload.get(key) != value:
                return False
        return True


@pytest.fixture
def test_settings(tmp_path, monkeypatch) -> Settings:
    get_settings.cache_clear()
    demo_path = tmp_path / "demo_knowledge"
    demo_path.mkdir()
    (demo_path / "hr-handbook.md").write_text(
        "# HR Handbook\n\nVacation policy: 20 days per year for full-time staff.\n",
        encoding="utf-8",
    )
    (demo_path / "it-support-guide.md").write_text(
        "# IT Support\n\nReset password via the self-service portal.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("GENERATION_PROVIDER", "mock")
    monkeypatch.setenv("RERANKING_PROVIDER", "none")
    monkeypatch.setenv("DEMO_KNOWLEDGE_PATH", str(demo_path))
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        embedding_provider="mock",
        generation_provider="mock",
        reranking_provider="none",
        demo_knowledge_path=str(demo_path),
        project_root=tmp_path,
    )


@pytest_asyncio.fixture
async def db_session(test_settings: Settings) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(test_settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = session_factory()
    try:
        yield session
        await session.commit()
    finally:
        await session.close()
        await engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def mock_embedding() -> MockEmbeddingProvider:
    return MockEmbeddingProvider()


@pytest.fixture
def mock_qdrant(test_settings: Settings) -> MockQdrantService:
    return MockQdrantService(test_settings)


@pytest_asyncio.fixture
async def api_client(
    mock_qdrant: MockQdrantService,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    from app.db.session import get_db

    engine = create_async_engine(test_settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.state.qdrant = mock_qdrant  # type: ignore[assignment]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def sample_parsed_document():
    from app.schemas.common import ParsedDocument

    return ParsedDocument(
        text="This is a test document. It has multiple sentences. Each sentence adds content.",
        title="Test Document",
        metadata={"department": "HR"},
        sections=[{"title": "Introduction", "content": "This is a test document."}],
    )


@pytest.fixture
def sample_raw_document():
    from app.schemas.common import DocumentReference, RawDocument

    ref = DocumentReference(
        stable_id="test-stable-id",
        filename="test.md",
        source="test",
        checksum="abc123",
    )
    return RawDocument(
        reference=ref,
        content=b"# Test\n\nSample markdown content for parsing.",
        content_type="text/markdown",
    )
