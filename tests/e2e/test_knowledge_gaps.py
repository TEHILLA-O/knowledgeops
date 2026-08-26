"""E2E test for knowledge gap detection."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ConfidenceLevel
from app.knowledge_gaps.service import KnowledgeGapService
from app.repositories.knowledge_gap_repo import KnowledgeGapRepository


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_knowledge_gap_recorded_on_low_confidence(
    db_session: AsyncSession,
    test_settings,
) -> None:
    repo = KnowledgeGapRepository(db_session)
    service = KnowledgeGapService(repo, test_settings)

    gap = await service.record_from_query(
        "What is the Mars colonization subsidy policy?",
        confidence_level=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
        confidence_score=0.1,
        best_retrieval_score=0.05,
    )
    await db_session.commit()

    assert gap is not None
    assert gap.frequency == 1
    assert gap.status == "UNRESOLVED"

    gap2 = await service.record_from_query(
        "What is the Mars colonization subsidy policy?",
        confidence_level=ConfidenceLevel.LOW,
        confidence_score=0.2,
    )
    await db_session.commit()
    assert gap2 is not None
    assert gap2.frequency == 2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_unsupported_query_creates_gap_via_api(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/query",
        json={"query": "What is the quantum flux capacitor maintenance schedule?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("INSUFFICIENT_EVIDENCE", "ANSWERED")

    gaps_response = await api_client.get("/api/v1/knowledge-gaps")
    assert gaps_response.status_code == 200
