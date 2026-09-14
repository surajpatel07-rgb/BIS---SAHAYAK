"""Retrieval service: query embedding → vector search → metadata filter → rerank.

Produces the grounded context blocks used by the chat service and the LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import get_logger
from app.rag.embeddings import get_embedding_provider
from app.rag.reranker import rerank
from app.rag.vector_store import RetrievedChunk, vector_store

logger = get_logger("app.rag.retrieval")


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    prompt_context: str = ""


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
    ) -> list[RetrievedChunk]:
        provider = get_embedding_provider()
        query_embedding = provider.embed_query(query)

        top_k = top_k or settings.retrieval_top_k
        candidates = vector_store.search(
            db,
            query_embedding=query_embedding,
            top_k=top_k,
            document_ids=document_ids,
            mode=mode,
            query_text=query or query_text,
        )

        candidates = rerank(
            query,
            candidates,
            top_n=settings.rerank_top_n,
            vector_weight=0.35,
        )
        logger.info("query=%r -> %s candidates -> %s after rerank", query, top_k, len(candidates))
        return candidates


def build_prompt(
    question: str,
    mode: str,
    history: list[dict],
    chunks: list[RetrievedChunk],
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
    closing = (
        "Decide the answer mode per your system instructions: if this is a BIS/standards "
        "question the retrieved context can support, answer ONLY from the context and cite "
        "blocks as [1], [2], ... immediately after the sentences that rely on them; "
        "otherwise reply as a transparent general-knowledge answer starting with the "
        "[GENERAL ANSWER] line and no [n] markers."
    )
    return (
        f"{mode_note}\n\n"
        f"RETRIEVED CONTEXT (numbered blocks; cite as [n]):\n\n{context}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"{closing}"
    )


def build_history(messages: list[dict], max_turns: int = 8) -> list[dict]:
    """Trim history to the last N messages for conversational context."""
    return messages[-max_turns:]
