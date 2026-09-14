"""Search endpoints: semantic chunk-level search + document metadata search."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.dependencies import get_current_user
from app.knowledge.registry import normalize_category
from app.models import Document, DocumentChunk, User
from app.rag.retrieval import RetrievalService
from app.schemas.documents import DocumentDetailOut, SearchHit, SemanticSearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SemanticSearchResponse)
def semantic_search(
    q: str = Query(min_length=1, max_length=1000),
    top_k: int = Query(default=8, ge=1, le=30),
    document_id: int | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Semantic search across indexed document chunks with reranking.

    category applies a hard metadata filter when given (search UI filter).
    """
    chunks = RetrievalService().retrieve(
        db,
        q,
        top_k=max(top_k * 2, 12),
        document_ids=[document_id] if document_id else None,
        categories=[normalize_category(category)] if category else None,
    )
    hits = [
        SearchHit(
            document_id=c.document_id,
            document_name=c.document_name,
            standard_number=c.standard_number,
            title=c.title,
            page=c.page_number,
            section=c.section,
            snippet=c.chunk_text[:300],
            score=round(c.score, 4),
            category=c.category,
            year=c.year,
        )
        for c in chunks[:top_k]
    ]
    return SemanticSearchResponse(query=q, results=hits)


@router.get("/documents", response_model=list[DocumentDetailOut])
def document_search(
    q: str | None = None,
    category: str | None = None,
    document_type: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Metadata search over indexed document records (number, title, keyword)."""
    query = db.query(Document).filter(Document.status == "indexed")
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Document.name.ilike(like))
            | (Document.title.ilike(like))
            | (Document.standard_number.ilike(like))
            | (Document.description.ilike(like))
        )
    if category:
        query = query.filter(Document.category == category)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    docs = query.order_by(Document.standard_number).limit(50).all()

    out: list[DocumentDetailOut] = []
    for d in docs:
        item = DocumentDetailOut.model_validate(d)
        item.chunk_count = (
            db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
        )
        out.append(item)
    return out
