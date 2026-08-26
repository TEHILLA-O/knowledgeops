"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import MockQdrantService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_root_endpoint(api_client: AsyncClient) -> None:
    response = await api_client.get("/")
    assert response.status_code == 200
    assert "KnowledgeOps" in response.json()["message"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint(
    api_client: AsyncClient,
    mock_qdrant: MockQdrantService,
) -> None:
    ingest_response = await api_client.post("/api/v1/ingestion/run", json={"source": "demo"})
    assert ingest_response.status_code == 200

    query_response = await api_client.post(
        "/api/v1/query",
        json={"query": "What is the vacation policy?", "include_debug": True},
    )
    assert query_response.status_code == 200
    data = query_response.json()
    assert "answer" in data
    assert "status" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_endpoint(api_client: AsyncClient) -> None:
    await api_client.post("/api/v1/ingestion/run", json={"source": "demo"})
    response = await api_client.post(
        "/api/v1/search",
        json={"query": "password reset", "top_k": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "password reset"
    assert "results" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_documents_list_endpoint(api_client: AsyncClient) -> None:
    await api_client.post("/api/v1/ingestion/run", json={"source": "demo"})
    response = await api_client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 0
