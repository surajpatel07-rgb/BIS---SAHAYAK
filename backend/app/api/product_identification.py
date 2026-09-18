"""AI Product Identifier endpoints.

POST /api/product-identification  — image (+optional note) -> product
identification -> BIS standard matching through the existing RAG pipeline.
POST /api/product-identification/match-standard — user-confirmed/edited product
name -> BIS standard matching (used after disambiguation or manual entry).

Honesty policy:
- Standards come ONLY from retrieved knowledge-base chunks (real RAG), never
  from the LLM's memory. Evidence confidence is derived from the retrieval
  scores, not asserted by a model.
- A match is labelled "potentially applicable / recommended for verification"
  unless a retrieved chunk explicitly supports applicability for the product.
- Empty/weak retrieval => needs_verification=True with the honest warning.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.dependencies import get_current_user
from app.logging_config import get_logger
from app.models import User
from app.config import settings
from app.knowledge.registry import find_product, normalize_category
from app.rag.query_understanding import understand_query
from app.rag.retrieval import RetrievalService
from app.rag.vector_store import RetrievedChunk
from app.rag.vision import (
    IdentificationUnavailable,
    Identification,
    VisionError,
    identification_to_query,
    image_quality_flags,
    validate_image,
)
from app.schemas.product_identification import (
    IdentifiedProduct,
    MatchStandardRequest,
    PossibleProduct,
    ProductIdentificationResponse,
    StandardRecommendation,
)

logger = get_logger("app.api.product_identification")
router = APIRouter(prefix="/api/product-identification", tags=["product-identification"])

# Evidence-confidence thresholds derived from the retrieval rerank score.
_STRONG = 0.45
_MODERATE = 0.25

_NO_MATCH_NOTICE = (
    "No sufficiently relevant BIS Standard was found in the current knowledge "
    "base. This does not necessarily mean that no applicable standard exists."
)
_UNCERTAIN_IDENT = (
    "Product identification is uncertain. Please upload a clearer image or "
    "provide additional details."
)


def _confidence_band(score: float) -> str:
    if score >= _STRONG:
        return "High"
    if score >= _MODERATE:
        return "Medium"
    return "Low"


def _match_level(score: float) -> str:
    if score >= _STRONG:
        return "strong"
    if score >= _MODERATE:
        return "moderate"
    return "weak"


def _evidence_snippet(chunk: RetrievedChunk) -> str:
    """Short evidence quote from the retrieved chunk (first sentences)."""
    text = " ".join(chunk.chunk_text.split())
    return text[:300] + ("…" if len(text) > 300 else "")


def _relevance_reason(chunk: RetrievedChunk, ident: Identification | None) -> str:
    """Grounded 'why this standard appears applicable' from retrieval facts."""
    bits: list[str] = []
    if chunk.standard_number:
        bits.append(f"retrieved for standard {chunk.standard_number}")
    if chunk.category:
        bits.append(f"from the {chunk.category.replace('_', ' ')} knowledge area")
    if ident and ident.product_name and ident.product_name.lower() in chunk.chunk_text.lower():
        bits.append(f"explicitly mentions “{ident.product_name}”")
    if chunk.section:
        bits.append(f"section “{chunk.section}”")
    return "; ".join(bits) if bits else "semantically matched the identified product"


def _recommendations(
    chunks: list[RetrievedChunk], ident: Identification | None
) -> list[StandardRecommendation]:
    recs: list[StandardRecommendation] = []
    for c in chunks:
        recs.append(
            StandardRecommendation(
                is_number=c.standard_number or "",
                title=c.title or c.document_name,
                relevance=_relevance_reason(c, ident),
                evidence=_evidence_snippet(c),
                source=f"{c.document_name}, page {c.page_number}"
                + (f" ({c.section})" if c.section else ""),
                source_url=c.source_url or "",
                document_id=c.document_id,
                page=c.page_number,
                section=c.section or "",
                category=c.category,
                confidence=round(float(c.score), 4),
                match_level=_match_level(float(c.score)),
            )
        )
    return recs


def _identify_product_model(ident: Identification) -> IdentifiedProduct:
    return IdentifiedProduct(
        name=ident.product_name,
        category=ident.category,
        confidence=round(ident.confidence, 3),
        product_type=ident.product_type,
        brand=ident.brand,
        model=ident.model,
        specifications=ident.specifications,
        markings=ident.markings,
        packaging_info=ident.packaging_info,
        possible_matches=[
            PossibleProduct(name=m.name, confidence=round(m.confidence, 3))
            for m in ident.possible_matches
        ],
    )


def _run_matching(
    db: Session, query: str, ident: Identification | None, warnings: list[str]
) -> ProductIdentificationResponse:
    """Shared stage 2: existing query understanding + retrieval over the KB."""
    u = understand_query(query)
    retrieval = RetrievalService()
    try:
        chunks = retrieval.retrieve(db, query, understanding=u)
    except Exception as exc:  # noqa: BLE001 — retrieval/embedding failure
        logger.error("RAG retrieval failed during product matching: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The BIS knowledge base is temporarily unavailable. Please try again.",
        ) from exc

    # Evidence validation: drop chunks whose score is below the app-wide
    # minimum relevance, and require non-trivial text.
    valid = [c for c in chunks if c.score >= settings.min_relevance_score and c.chunk_text.strip()]
    standards = _recommendations(valid, ident)

    # Evidence validation verdict: a confident recommendation needs at least
    # one STRONG match; anything less is explicitly flagged for verification.
    best = max((r.confidence for r in standards), default=0.0)
    if not standards:
        needs_verification = True
        warnings.append(_NO_MATCH_NOTICE)
    elif best < _STRONG:
        needs_verification = True
        warnings.append(
            "Only weakly relevant documents were found. Treat these as leads for "
            "verification rather than confirmed applicability."
        )
    else:
        needs_verification = False

    product = _identify_product_model(ident) if ident else IdentifiedProduct(
        name="", category="", confidence=0.0
    )
    # A user-confirmed match has no disambiguation list to carry.
    if ident is None:
        product.possible_matches = []

    return ProductIdentificationResponse(
        product=product,
        standards=standards,
        warnings=warnings,
        needs_verification=needs_verification,
        query_used=query,
        llm_provider="gemini" if settings.llm_available else "fallback",
    )


@router.post("", response_model=ProductIdentificationResponse)
async def identify_product(
    image: UploadFile = File(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Identify a product from an image, then match BIS standards via RAG."""
    # 1) Validate image type/size (real validation, no silent accepts)
    try:
        data = await image.read()
        validate_image(data, image.filename or "", image.content_type or "")
    except VisionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    finally:
        await image.close()

    warnings = image_quality_flags(data)

    # 2) Vision identification (one multimodal call)
    try:
        from app.rag.vision import identify_product as vision_identify

        ident = vision_identify(data, description or "")
    except IdentificationUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except VisionError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    # 3) Honest handling of uncertain identification
    if not ident.confident:
        warnings.insert(0, _UNCERTAIN_IDENT)
        # Still run matching with whatever query can be formed, so the user
        # gets leads; the UI labels identification as low confidence.
    if warnings:
        # de-duplicate while preserving order
        warnings = list(dict.fromkeys(warnings))

    query = identification_to_query(ident, description or "")
    response = _run_matching(db, query, ident, warnings)

    # If identification was uncertain, the standard list must not read as
    # confident: mark verification needed so the UI shows the notice.
    if not ident.confident and response.standards:
        response.needs_verification = True
    return response


@router.post("/match-standard", response_model=ProductIdentificationResponse)
def match_standard(
    payload: MatchStandardRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Match BIS standards for a user-confirmed/edited product name."""
    name = payload.product_name.strip()
    category_note = ""
    if payload.category.strip():
        cat = normalize_category(payload.category)
        category_note = f" ({cat.replace('_', ' ')})" if cat else ""
    query = f"BIS standard requirements for {name}{category_note}"

    # Registry product hit? Enrich the query with its canonical name so the
    # retrieval query matches how documents reference the product.
    product = find_product(name)
    if product and product.name.lower() not in query.lower():
        query = f"BIS standard requirements for {product.name} ({name})"

    ident = Identification(product_name=name, category=payload.category, confidence=1.0)
    return _run_matching(db, query, ident, warnings=[])
