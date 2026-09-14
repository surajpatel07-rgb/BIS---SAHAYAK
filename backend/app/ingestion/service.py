"""Document ingestion service: upload → extract → clean → chunk → embed → index.

The pipeline updates Document.status at every stage so the admin UI can show
real progress (uploaded → processing → extracting → chunking → embedding →
indexed | failed). Failures are recorded on the document row, never swallowed.
"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import get_logger
from app.models import Document, DocumentChunk
from app.rag.chunking import chunk_text, clean_text
from app.rag.embeddings import get_embedding_provider
from app.config import BASE_DIR

logger = get_logger("app.ingestion.service")

_pdf_path = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {".pdf"}


class IngestionError(Exception):
    """Raised for validation or processing failures the API should report."""


def validate_pdf(filename: str, content: bytes) -> None:
    """Validate extension, size, and PDF magic bytes."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise IngestionError("Only PDF files are allowed")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise IngestionError(f"File exceeds the {settings.max_upload_mb} MB limit")
    if len(content) < 100:
        raise IngestionError("File is too small to be a valid PDF")
    if not content.startswith(b"%PDF"):
        raise IngestionError("Not a valid PDF file (missing %PDF header)")


def generate_stored_name(original: str) -> str:
    """Build a safe stored filename: uuid prefix + sanitized original name."""
    suffix = Path(original).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(original).stem)[:80] or "document"
    return f"{secrets.token_hex(8)}_{stem}{suffix}"


def _guess_metadata(doc: Document, text: str) -> None:
    """Fill title/year/standard number if missing using simple heuristics."""
    if not doc.standard_number:
        m = re.search(r"\bIS\s*/?\s*(\d{3,5})\s*[:：]?\s*(\d{4})?", text[:3000])
        if m:
            doc.standard_number = f"IS {m.group(1)}" + (f":{m.group(2)}" if m.group(2) else "")
    if not doc.year:
        m = re.search(r"\b(19|20)\d{2}\b", text[:3000])
        if m:
            doc.year = int(m.group(0))


def ingest_document(db: Session, document_id: int) -> Document:
    """Run the full ingestion pipeline for a previously created Document row.

    Raises IngestionError on failure (after marking the document failed).
    """
    from app.knowledge.registry import normalize_category

    document = db.get(Document, document_id)
    if document is None:
        raise IngestionError(f"Document {document_id} not found")

    try:
        # Normalize the category to a canonical registry key at ingest time.
        document.category = normalize_category(document.category)
        document.status = "processing"
        db.commit()

        # 1) Extract -------------------------------------------------------
        document.status = "extracting"
        db.commit()
        from app.ingestion.pdf import extract_pdf

        path = Path(document.file_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        extracted = extract_pdf(str(path))
        document.page_count = extracted.page_count

        # 2) Clean ---------------------------------------------------------
        document.status = "chunking"
        db.commit()
        cleaned = clean_text(extracted.text)

        # 3) Chunk ---------------------------------------------------------
        chunks = chunk_text(cleaned, page_starts=extracted.page_starts)
        if not chunks:
            raise IngestionError("No content chunks could be produced from this document")
        logger.info(
            "doc=%s extracted %s pages -> %s chunks", document_id, extracted.page_count, len(chunks)
        )

        # 4) Embed ---------------------------------------------------------
        document.status = "embedding"
        db.commit()
        provider = get_embedding_provider()
        texts = [c.text for c in chunks]
        embeddings = provider.embed(texts)
        if len(embeddings) != len(chunks):
            raise IngestionError("Embedding provider returned mismatched vector count")

        # 5) Index ---------------------------------------------------------
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_id=i,
                    chunk_text=chunk.text,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    embedding=emb,
                    embedding_model=provider.name,
                    meta={
                        "document_id": document.id,
                        "document_name": document.name,
                        "standard_number": document.standard_number,
                        "title": document.title,
                        "category": document.category,
                        "subcategory": document.subcategory,
                        "product_name": document.product_name,
                        "source_type": document.source_type,
                        "source_name": document.source_name,
                        "source_url": document.source_url,
                        "language": document.language,
                        "publication_year": document.year,
                        "sequence": i,
                    },
                )
            )

        _guess_metadata(document, cleaned)

        # Sync StandardMetadata so explicitly-numbered documents appear in the
        # standards catalog (only for numbers the registry knows, or any
        # admin-declared number — never invented ones).
        if document.standard_number:
            from app.models import StandardMetadata

            existing = (
                db.query(StandardMetadata)
                .filter(StandardMetadata.standard_number == document.standard_number)
                .first()
            )
            if not existing:
                db.add(
                    StandardMetadata(
                        standard_number=document.standard_number,
                        title=document.title or document.name,
                        category=document.category,
                        product_name=document.product_name,
                    )
                )

        document.status = "indexed"
        document.error_message = ""
        db.commit()
        logger.info("doc=%s indexed with %s chunks", document.id, len(chunks))
        return document

    except IngestionError as exc:
        db.rollback()
        document.status = "failed"
        document.error_message = str(exc)
        db.commit()
        logger.error("Ingestion failed for doc=%s: %s", document_id, exc)
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        document.status = "failed"
        document.error_message = f"Unexpected error: {exc}"
        db.commit()
        logger.exception("Ingestion crashed for doc=%s", document_id)
        raise IngestionError(f"Ingestion failed: {exc}") from exc
