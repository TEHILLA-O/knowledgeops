"""Permission filtering for retrieved chunks."""

from app.core.constants import UserGroup
from app.core.logging import get_logger
from app.schemas.common import RetrievedChunk

logger = get_logger(__name__)


def _normalize_groups(groups: list[str] | str | None) -> set[str]:
    if groups is None:
        return set()
    if isinstance(groups, str):
        return {groups.upper()}
    return {g.upper() for g in groups if g}


def chunk_allowed_for_user(chunk: RetrievedChunk, user_group: str | None) -> bool:
    """Return True when the user may access this chunk."""
    if not user_group:
        return True

    allowed = _normalize_groups(chunk.metadata.get("allowed_groups"))
    if not allowed:
        return True

    user = user_group.upper()
    if UserGroup.ALL.value in allowed:
        return True
    return user in allowed


class PermissionFilter:
    """Filters chunks by user group and document allowed_groups before generation."""

    def filter_chunks(
        self,
        chunks: list[RetrievedChunk],
        user_group: str | None,
    ) -> list[RetrievedChunk]:
        if not user_group:
            return chunks

        allowed_chunks = [c for c in chunks if chunk_allowed_for_user(c, user_group)]
        removed = len(chunks) - len(allowed_chunks)
        if removed:
            logger.info(
                "permission_filter_applied",
                user_group=user_group,
                removed=removed,
                remaining=len(allowed_chunks),
            )
        return allowed_chunks
