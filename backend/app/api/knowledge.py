"""Knowledge-base endpoints: categories, product explorer, product detail,
category-aware search and admin RAG debugging."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.dependencies import get_current_user, require_admin
from app.knowledge.registry import (
    CATEGORIES,
    find_product,
    normalize_category,
    related_questions_for,
)
from app.models import Document, DocumentChunk, Product as ProductRow
from app.models import ProductCategory, StandardMetadata
from app.rag.retrieval import RetrievalService

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """All knowledge categories with live per-category document counts."""
    counts = dict(
        db.query(Document.category, func.count(Document.id))
        .filter(Document.status == "indexed")
        .group_by(Document.category)
        .all()
    )
    return [
        {
            "key": key,
            "label": cat.label,
            "emoji": cat.emoji,
            "description": cat.description,
            "document_count": int(counts.get(key, 0)),
        }
        for key, cat in CATEGORIES.items()
    ]


# ---------------------------------------------------------------------------
# Product explorer
# ---------------------------------------------------------------------------
@router.get("/products")
def list_products(
    category: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Products from the registry (DB-backed, registry-synced)."""
    query = db.query(ProductRow)
    if category:
        query = query.filter(ProductRow.category == normalize_category(category))
    if q:
        like = f"%{q}%"
        query = query.filter(ProductRow.name.ilike(like) | ProductRow.subcategory.ilike(like))
    rows = query.order_by(ProductRow.category, ProductRow.name).all()
    return [_product_out(r) for r in rows]


def _product_out(r: ProductRow) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "category": r.category,
        "category_label": CATEGORIES.get(r.category).label if CATEGORIES.get(r.category) else r.category,
        "category_emoji": CATEGORIES.get(r.category).emoji if CATEGORIES.get(r.category) else "",
        "subcategory": r.subcategory,
        "standard_number": r.standard_number,
        "standard_title": r.standard_title,
        "certification_status": r.certification_status,
        "certification_status_display": _status_display(r.certification_status),
        "scheme": r.scheme,
        "consumer_checklist": r.checklist_json or [],
        "notes": r.notes,
        # Products whose BIS status is unknown carry an explicit flag so the
        # UI shows "Information not available in the current knowledge base".
        # A generic consumer checklist alone is not BIS information.
        "info_available": r.certification_status != "info-not-available",
    }


def _status_display(status: str) -> str:
    return {
        "mandatory": "Mandatory BIS certification (verify current QCO)",
        "voluntary": "BIS certification is voluntary for this product",
        "scheme-specific": "Certified under a BIS scheme (see notes)",
        "info-not-available": "Information not available in the current knowledge base",
    }.get(status, status)


@router.get("/products/{product_id}")
def product_detail(
    product_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Product detail page data: product info + related indexed documents."""
    row = db.get(ProductRow, product_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    docs = (
        db.query(Document)
        .filter(
            Document.status == "indexed",
            Document.category == row.category,
        )
        .order_by(Document.standard_number)
        .limit(12)
        .all()
    )
    # Prefer documents explicitly about this product when tagged
    product_docs = (
        db.query(Document)
        .filter(Document.status == "indexed", Document.product_name == row.name)
        .all()
    )
    related_doc_ids = {d.id for d in product_docs}
    out = _product_out(row)
    out["related_documents"] = [
        {
            "id": d.id,
            "name": d.name,
            "standard_number": d.standard_number,
            "title": d.title,
            "year": d.year,
            "source_type": d.source_type,
            "source_name": d.source_name,
        }
        for d in sorted(
            docs, key=lambda d: (d.id not in related_doc_ids, d.standard_number or "")
        )
    ]
    out["related_questions"] = related_questions_for(row.category, None)
    return out


# ---------------------------------------------------------------------------
# Standards catalog
# ---------------------------------------------------------------------------
@router.get("/standards")
def list_standards(
    q: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(StandardMetadata)
    if q:
        like = f"%{q}%"
        query = query.filter(
            StandardMetadata.standard_number.ilike(like) | StandardMetadata.title.ilike(like)
        )
    if category:
        query = query.filter(StandardMetadata.category == normalize_category(category))
    rows = query.order_by(StandardMetadata.standard_number).limit(200).all()
    return [
        {
            "standard_number": r.standard_number,
            "title": r.title,
            "category": r.category,
            "product_name": r.product_name,
            "status": r.status,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Knowledge-base statistics (admin)
# ---------------------------------------------------------------------------
@router.get("/stats")
def knowledge_stats(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Per-category document/chunk statistics — always from the live DB."""
    docs_by_cat = dict(
        db.query(Document.category, func.count(Document.id))
        .group_by(Document.category)
        .all()
    )
    chunk_counts = dict(
        db.query(Document.category, func.count(DocumentChunk.id))
        .join(DocumentChunk, DocumentChunk.document_id == Document.id)
        .group_by(Document.category)
        .all()
    )
    indexed_by_cat = dict(
        db.query(Document.category, func.count(Document.id))
        .filter(Document.status == "indexed")
        .group_by(Document.category)
        .all()
    )
    failed_by_cat = dict(
        db.query(Document.category, func.count(Document.id))
        .filter(Document.status == "failed")
        .group_by(Document.category)
        .all()
    )
    last_updated = (
        db.query(func.max(Document.updated_at)).scalar()
    )
    categories = []
    for key, cat in CATEGORIES.items():
        categories.append(
            {
                "key": key,
                "label": cat.label,
                "emoji": cat.emoji,
                "documents": int(docs_by_cat.get(key, 0)),
                "indexed": int(indexed_by_cat.get(key, 0)),
                "chunks": int(chunk_counts.get(key, 0)),
                "failed": int(failed_by_cat.get(key, 0)),
            }
        )
    return {
        "categories": categories,
        "total_products": db.query(func.count(ProductRow.id)).scalar() or 0,
        "total_standards": db.query(func.count(StandardMetadata.id)).scalar() or 0,
        "last_updated": last_updated.isoformat() if last_updated else None,
    }


# ---------------------------------------------------------------------------
# RAG debugging panel (admin only)
# ---------------------------------------------------------------------------
@router.get("/debug/retrieval")
def rag_debug(
    q: str = Query(min_length=1, max_length=1000),
    document_ids: str | None = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Full retrieval trace: detection, candidates, scores, selected context."""
    ids = None
    if document_ids:
        try:
            ids = [int(x) for x in document_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "document_ids must be ints") from None
    result = RetrievalService().retrieve_with_trace(db, q, document_ids=ids)
    return result.debug_trace
