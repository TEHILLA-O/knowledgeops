"""Document routes."""

import math

from fastapi import APIRouter, Depends, Query

from app.api.deps import Repositories, get_repositories
from app.db.models import Document
from app.schemas.common import DocumentSummary, DocumentVersionInfo, PaginatedResponse

router = APIRouter(prefix="/documents", tags=["documents"])


def _document_to_summary(doc: Document) -> DocumentSummary:
    return DocumentSummary(
        id=doc.id,
        stable_id=doc.stable_id,
        title=doc.title,
        filename=doc.filename,
        document_type=doc.document_type,
        source=doc.source,
        current_version=doc.current_version,
        status=doc.status,
        department=doc.department,
        chunk_count=doc.chunk_count,
        is_deleted=doc.is_deleted,
        last_indexed_at=doc.last_indexed_at,
    )


@router.get("", response_model=PaginatedResponse)
@router.get("/", response_model=PaginatedResponse, include_in_schema=False)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source: str | None = None,
    document_type: str | None = None,
    department: str | None = None,
    status: str | None = None,
    search: str | None = None,
    repos: Repositories = Depends(get_repositories),
) -> PaginatedResponse:
    items, total = await repos.documents.list_documents(
        page=page,
        page_size=page_size,
        source=source,
        document_type=document_type,
        department=department,
        status=status,
        search=search,
    )
    pages = math.ceil(total / page_size) if total else 0
    return PaginatedResponse(
        items=[_document_to_summary(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{document_id}", response_model=DocumentSummary)
async def get_document(
    document_id: str,
    repos: Repositories = Depends(get_repositories),
) -> DocumentSummary:
    doc = await repos.documents.get_by_id(document_id)
    return _document_to_summary(doc)


@router.get("/{document_id}/versions", response_model=list[DocumentVersionInfo])
async def get_document_versions(
    document_id: str,
    repos: Repositories = Depends(get_repositories),
) -> list[DocumentVersionInfo]:
    versions = await repos.documents.get_versions(document_id)
    return [
        DocumentVersionInfo(
            id=v.id,
            version=v.version,
            content_hash=v.content_hash,
            status=v.status,
            discovered_at=v.discovered_at,
            indexed_at=v.indexed_at,
        )
        for v in versions
    ]
