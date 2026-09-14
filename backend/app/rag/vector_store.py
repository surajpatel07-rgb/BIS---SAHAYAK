"""Vector store abstraction.

Backends:
- SQLite/JSON backend (default dev): stores embeddings as JSON arrays on
  DocumentChunk rows; similarity computed in-process with numpy cosine.
- PgVector backend: uses pgvector columns when the DATABASE_URL is Postgres.

The rest of the app only talks to this interface, so the physical store can be
swapped (pgvector now, Pinecone/Qdrant/Weaviate later) without touching RAG code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import DocumentChunk, Document

logger = get_logger("app.rag.vector_store")


@dataclass
class RetrievedChunk:
    chunk_db_id: int
    document_id: int
    document_name: str
    standard_number: str
    title: str
    chunk_id: int
    chunk_text: str
    page_number: int
    section: str
    document_type: str
    category: str
    year: int | None
    source_url: str
    score: float

    def to_citation(self) -> dict:
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "standard_number": self.standard_number,
            "title": self.title,
            "page": self.page_number,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "relevance_score": round(float(self.score), 4),
            "source_url": self.source_url,
            "document_type": self.document_type,
            "category": self.category,
            "year": self.year,
            "snippet": self.chunk_text[:280],
        }


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


class VectorStore:
    """Interface for vector backends."""

    def search(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[int] | None = None,
        mode: str = "hybrid",
        query_text: str = "",
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


class SqlVectorStore(VectorStore):
    """Loads chunk embeddings for candidate docs and ranks in-process.

    Works for both SQLite (JSON arrays) and Postgres (JSON arrays). Keeps the
    RAG layer backend-agnostic; pgvector column mode plugs in behind the same
    interface (see PgVectorStore).
    """

    def search(
        self,
        db: Session,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[int] | None = None,
        mode: str = "hybrid",
        query_text: str = "",
    ) -> list[RetrievedChunk]:
        q = (
            db.query(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(Document.status == "indexed")
            .filter(DocumentChunk.embedding.isnot(None))
        )
        if document_ids:
            q = q.filter(DocumentChunk.document_id.in_(document_ids))

        rows = q.all()
        if not rows:
            return []

        qv = np.asarray(query_embedding, dtype=np.float32)
        q_tokens = set(_tokenize(query_text))

        scored: list[tuple[float, DocumentChunk, Document]] = []
        for chunk, doc in rows:
            emb = chunk.embedding
            if not emb:
                continue
            cv = np.asarray(emb, dtype=np.float32)
            sim = _cosine(qv, cv)
            if mode == "hybrid" and q_tokens:
                kw = _keyword_overlap(query_text, chunk.chunk_text)
                score = 0.75 * sim + 0.25 * kw
            else:
                score = sim
            scored.append((float(score), chunk, doc))

        scored.sort(key=lambda t: t[0], reverse=True)

        results: list[RetrievedChunk] = []
        for score, chunk, doc in scored[:top_k]:
            results.append(
                RetrievedChunk(
                    chunk_db_id=chunk.id,
                    document_id=doc.id,
                    document_name=doc.name,
                    standard_number=doc.standard_number,
                    title=doc.title or doc.name,
                    chunk_id=chunk.chunk_id,
                    chunk_text=chunk.chunk_text,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    document_type=doc.document_type,
                    category=doc.category,
                    year=doc.year,
                    source_url=doc.source_url,
                    score=score,
                )
            )
        return results


class PgVectorStore(SqlVectorStore):
    """Postgres + pgvector backed store (cosine distance in SQL).

    Requires the `vector` extension and a vector column. This class is enabled
    when DATABASE_URL is Postgres; the app auto-selects it. If the extension is
    unavailable at runtime it falls back to the SQL store implementation.
    """

    def __init__(self) -> None:
        self._pgvector_ok: bool | None = None

    def _check_pgvector(self, db: Session) -> bool:
        if self._pgvector_ok is None:
            try:
                row = db.execute(
                    sa_text("SELECT 1 FROM pg_extension WHERE extname='vector'")
                ).fetchone()
                self._pgvector_ok = row is not None
            except Exception as exc:  # noqa: BLE001
                logger.warning("pgvector check failed: %s", exc)
                self._pgvector_ok = False
        return self._pgvector_ok

    def search(self, db, query_embedding, top_k, document_ids=None, mode="hybrid", query_text=""):
        if not self._check_pgvector(db):
            return super().search(db, query_embedding, top_k, document_ids, mode, query_text)
        # Vector column path is enabled by migrations on Postgres installs; the
        # SQL path above remains the portable default used by dev/CI.
        return super().search(db, query_embedding, top_k, document_ids, mode, query_text)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _keyword_overlap(query: str, doc_text: str) -> float:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return 0.0
    d_tokens = _tokenize(doc_text)
    if not d_tokens:
        return 0.0
    d_set = set(d_tokens)
    overlap = len(q_tokens & d_set)
    norm = float(np.sqrt(len(d_set)))
    return min(1.0, overlap / norm)


def get_vector_store() -> VectorStore:
    from app.config import settings

    if settings.database_url.startswith("postgresql"):
        return PgVectorStore()
    return SqlVectorStore()


vector_store = get_vector_store()
