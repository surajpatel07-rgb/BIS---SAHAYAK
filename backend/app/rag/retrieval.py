"""Retrieval service: query embedding → vector search → metadata filter → rerank.

Produces the grounded context blocks used by the chat service and the LLM.

Knowledge-category awareness:
- The query-understanding service detects the knowledge category (food,
  hallmarking, ...) and it is applied as a metadata pre-filter when confident,
  else as a rerank boost (see reranker.category_boost) so the most
  category-relevant chunks win without excluding borderline evidence.
- Source priority: chunks from OFFICIAL_BIS > GOVERNMENT > OFFICIAL > DEMO
  sources get progressively smaller blending weights, so official material
  ranks higher than demo data at equal similarity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import get_logger
from app.rag.embeddings import get_embedding_provider
from app.rag.query_understanding import understand_query
from app.rag.reranker import rerank
from app.rag.vector_store import RetrievedChunk, vector_store

logger = get_logger("app.rag.retrieval")

# Source-priority blending weights by document source_type. Official sources
# keep more of their vector score; demo data is damped so it only wins when
# genuinely more similar.
_SOURCE_WEIGHTS = {
    "official_bis": 1.0,
    "government": 0.95,
    "official": 0.9,
    "demo": 0.8,
}

# Rerank category-boost magnitude by detection confidence.
_CONFIDENT_CATEGORY = 0.7  # >= product match / explicit standard number


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    prompt_context: str = ""
    understanding: object | None = None  # QueryUnderstanding
    debug_trace: dict = field(default_factory=dict)


def _format_context(chunks: list[RetrievedChunk]) -> str:
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        header = (
            f"[{i}] Source: {c.document_name}"
            + (f" | Standard: {c.standard_number}" if c.standard_number else "")
            + f" | Page {c.page_number}"
            + (f" | Section: {c.section}" if c.section else "")
        )
        lines.append(header)
        lines.append(c.chunk_text)
        lines.append("")
    return "\n".join(lines)


class RetrievalService:
    def retrieve(
        self,
        db: Session,
        query: str,
        top_k: int | None = None,
        document_ids: list[int] | None = None,
        mode: str = "hybrid",
        query_text: str = "",
        categories: list[str] | None = None,
        understanding=None,
        debug: bool = False,
    ) -> list[RetrievedChunk]:
        """Retrieve + rerank chunks for a query.

        categories: explicit category filter (e.g. from the search UI). When
        None, the query-understanding detection decides (filter if confident,
        boost otherwise).
        understanding: optionally pass a precomputed QueryUnderstanding to
        avoid re-classifying (the chat endpoint does this once per query).
        """
        from app.knowledge.registry import CATEGORIES, related_categories_for

        u = understanding or understand_query(query)
        effective_query = query or query_text
        provider = get_embedding_provider()
        query_embedding = provider.embed_query(effective_query)

        # Category strategy: explicit filter wins; confident detection filters
        # (widened to related categories so e.g. a water question can still hit
        # food/packaging documents); weak detection boosts only.
        used_filter: list[str] | None = categories
        category_boost = 0.0
        if used_filter is None:
            if u.category_confidence >= _CONFIDENT_CATEGORY and u.category in CATEGORIES:
                used_filter = [u.category, *related_categories_for(u.category)]
            elif u.category_confidence > 0.15 and u.category in CATEGORIES:
                category_boost = min(0.12, u.category_confidence * 0.15)

        top_k = top_k or settings.retrieval_top_k
        candidates = vector_store.search(
            db,
            query_embedding=query_embedding,
            top_k=max(top_k * 3, 24),
            document_ids=document_ids,
            mode=mode,
            query_text=effective_query,
            categories=used_filter,
        )

        # Source-priority damping applied before rerank blending.
        for c in candidates:
            w = _SOURCE_WEIGHTS.get(getattr(c, "source_type", "demo"), 0.8)
            c.score *= w
            c.category_boost = category_boost

        candidates = rerank(
            effective_query,
            candidates,
            top_n=settings.rerank_top_n,
            vector_weight=0.35,
            category_boost=category_boost,
        )
        logger.info(
            "query=%r -> cat=%s(%s) filter=%s -> %s after rerank",
            effective_query, u.category, round(u.category_confidence, 2),
            used_filter, len(candidates),
        )
        return candidates

    def retrieve_with_trace(
        self,
        db: Session,
        query: str,
        mode: str = "hybrid",
        document_ids: list[int] | None = None,
    ) -> RetrievalResult:
        """retrieve() + a debug trace for the admin RAG debugging panel."""
        u = understand_query(query)
        provider = get_embedding_provider()
        qv = provider.embed_query(query)

        candidates = vector_store.search(
            db,
            query_embedding=qv,
            top_k=max(settings.retrieval_top_k * 3, 24),
            document_ids=document_ids,
            mode=mode,
            query_text=query,
        )
        pre_rerank = [
            {
                "document_id": c.document_id,
                "document_name": c.document_name,
                "standard_number": c.standard_number,
                "page": c.page_number,
                "section": c.section,
                "category": c.category,
                "source_type": getattr(c, "source_type", "demo"),
                "vector_score": round(float(c.score), 4),
            }
            for c in candidates
        ]

        for c in candidates:
            w = _SOURCE_WEIGHTS.get(getattr(c, "source_type", "demo"), 0.8)
            c.score *= w
            c.category_boost = min(0.12, u.category_confidence * 0.15) if u.category_confidence > 0.15 else 0.0

        final = rerank(
            query,
            list(candidates),
            top_n=settings.rerank_top_n,
            vector_weight=0.35,
            category_boost=min(0.12, u.category_confidence * 0.15) if u.category_confidence > 0.15 else 0.0,
        )

        trace = {
            "query": query,
            "language": u.language,
            "detected_category": u.category,
            "category_confidence": round(u.category_confidence, 3),
            "matched_keywords": u.matched_keywords[:10],
            "matched_product": u.product_name,
            "detected_standard": u.standard_number,
            "category_filter_applied": u.category_confidence >= _CONFIDENT_CATEGORY and u.product_name != "",
            "candidates_before_rerank": pre_rerank,
            "selected_chunks": [
                {
                    "document_id": c.document_id,
                    "document_name": c.document_name,
                    "standard_number": c.standard_number,
                    "page": c.page_number,
                    "section": c.section,
                    "category": c.category,
                    "final_score": round(float(c.score), 4),
                    "snippet": c.chunk_text[:160],
                }
                for c in final
            ],
            "final_context": _format_context(final)[:4000],
            "embedding_model": provider.name,
            "top_k": settings.retrieval_top_k,
            "rerank_top_n": settings.rerank_top_n,
        }
        return RetrievalResult(
            chunks=final,
            prompt_context=_format_context(final),
            understanding=u,
            debug_trace=trace,
        )


def build_prompt(
    question: str,
    mode: str,
    history: list[dict],
    chunks: list[RetrievedChunk],
    understanding=None,
) -> str:
    """Assemble the grounded prompt sent to the LLM (context + question).

    Context blocks are always provided when available; the closing instruction
    adapts to the hybrid answer modes (see app.rag.llm.SYSTEM_PROMPT): the
    model decides between a BIS-grounded answer (cite [n]) and a transparent
    general-knowledge answer ([GENERAL ANSWER], no citations).
    """
    context = _format_context(chunks)
    mode_note = (
        "USER MODE: CONSUMER — use simple language, focus on safety, product quality and "
        "how to verify the ISI mark / certification."
        if mode == "consumer"
        else "USER MODE: INDUSTRY — use precise, procedure-oriented language covering standards, "
        "compliance steps, documentation and testing requirements."
    )

    lang_note = ""
    if understanding is not None and getattr(understanding, "language", "en") == "hi":
        lang_note = (
            "\n\nLANGUAGE: The user asked in HINDI. Reply in simple Hindi (Devanagari "
            "script). Do NOT translate standard numbers or official document names — "
            "keep e.g. 'IS 14543' and 'Bureau of Indian Standards (BIS)' as-is."
        )

    category_note = ""
    if understanding is not None and getattr(understanding, "category", "general_bis") != "general_bis":
        cat_label = getattr(understanding, "category_label", "")
        product = getattr(understanding, "product_name", "")
        category_note = (
            f"\n\nDETECTED KNOWLEDGE AREA: {cat_label}"
            + (f" (product focus: {product})" if product else "")
            + ". Prefer retrieved context from this area when it is relevant; ignore "
            "retrieved blocks that are clearly unrelated."
        )

    closing = (
        "Decide the answer mode per your system instructions: if this is a BIS/standards "
        "question the retrieved context can support, answer ONLY from the context and cite "
        "blocks as [1], [2], ... immediately after the sentences that rely on them; "
        "otherwise reply as a transparent general-knowledge answer starting with the "
        "[GENERAL ANSWER] line and no [n] markers."
    )
    return (
        f"{mode_note}{lang_note}{category_note}\n\n"
        f"RETRIEVED CONTEXT (numbered blocks; cite as [n]):\n\n{context}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"{closing}"
    )


def build_history(messages: list[dict], max_turns: int = 8) -> list[dict]:
    """Trim history to the last N messages for conversational context."""
    return messages[-max_turns:]
