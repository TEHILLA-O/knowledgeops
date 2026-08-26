"""Tests for permission filtering."""

from app.retrieval.permissions import PermissionFilter, chunk_allowed_for_user
from app.schemas.common import RetrievedChunk


def _chunk(allowed_groups: list[str] | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        document_title="Doc",
        document_version=1,
        content="content",
        metadata={"allowed_groups": allowed_groups or []},
    )


def test_no_user_group_allows_all() -> None:
    assert chunk_allowed_for_user(_chunk(["FINANCE"]), None) is True


def test_empty_allowed_groups_public() -> None:
    assert chunk_allowed_for_user(_chunk([]), "ENGINEERING") is True


def test_restricted_chunk_blocked() -> None:
    assert chunk_allowed_for_user(_chunk(["FINANCE"]), "ENGINEERING") is False


def test_allowed_group_permitted() -> None:
    assert chunk_allowed_for_user(_chunk(["FINANCE"]), "FINANCE") is True


def test_permission_filter_removes_restricted() -> None:
    filt = PermissionFilter()
    chunks = [_chunk(["FINANCE"]), _chunk([])]
    result = filt.filter_chunks(chunks, "ENGINEERING")
    assert len(result) == 1
