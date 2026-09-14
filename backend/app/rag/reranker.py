"""Reranking layer.

Re-scores retrieval candidates using a stronger signal than first-stage
similarity: term-overlap between the query and chunk text combined with
semantic similarity already computed by the vector store, plus small boosts
for exact standard-number matches and metadata alignment.

This is a practical cross-encoder-free reranker: deterministic, fast, and
works offline. A cross-encoder (e.g. bge-reranker) can replace `score()`
later without touching the retrieval service.
"""
from __future__ import annotations

import re

from app.rag.vector_store import RetrievedChunk


def _tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "what", "which", "who", "how",
        "for", "of", "to", "and", "in", "on", "at", "by", "or", "from", "it", "its",
        "does", "do", "did", "i", "my", "me", "should", "can", "could", "this", "that",
        "with", "as", "be", "been", "will", "would", "there", "their", "have", "has",
    }
    return set(re.findall(r"[a-z0-9]+", text.lower())) - stop


def score_chunk(
    query: str,
    chunk: RetrievedChunk,
    category_boost: float = 0.0,
) -> float:
    """Blend query-term coverage, phrase match, and metadata boosts."""
    q_tokens = _tokens(query)
    c_tokens = _tokens(chunk.chunk_text)
    if not q_tokens or not c_tokens:
        return 0.0

    # 1) Query-term coverage in chunk (Jaccard-ish weighted recall)
    overlap = len(q_tokens & c_tokens)
    term_score = overlap / len(q_tokens)

    # 2) Exact phrase match bonus
    phrase = 0.15 if query.lower().strip() in chunk.chunk_text.lower() else 0.0

    # 3) Standard-number boost: "is 12345", "is:12345", "12345:2020"
    nums = set(re.findall(r"\b\d{3,5}\b", query))
    std_boost = 0.0
    if nums:
        chunk_nums = set(re.findall(r"\b\d{3,5}\b", chunk.standard_number))
        if nums & chunk_nums:
            std_boost = 0.25

    # 4) Title alignment bonus
    title_tokens = _tokens(chunk.title + " " + chunk.document_name)
    title_score = (len(q_tokens & title_tokens) / len(q_tokens)) * 0.1

    return min(1.0, 0.55 * term_score + phrase + std_boost + title_score + category_boost)


def rerank(
    query: str,
    candidates: list[RetrievedChunk],
    top_n: int = 5,
    vector_weight: float = 0.35,
    category_boost: float = 0.0,
) -> list[RetrievedChunk]:
    """Return the top_n candidates re-scored by the reranker.

    Final score = vector_weight * vector_score + (1 - vector_weight) * rerank_score.
    The blended score is written back into `relevance_score` for citations.
    """
    for c in candidates:
        rr = score_chunk(query, c, category_boost=category_boost)
        c.score = vector_weight * c.score + (1 - vector_weight) * rr
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]
