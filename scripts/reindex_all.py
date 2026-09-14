"""Re-ingest every document with the CURRENT embedding provider.

Run from the project root:
    python scripts/reindex_all.py            # actually re-embed
    python scripts/reindex_all.py --dry-run  # show what would happen

Use this after switching EMBEDDING_PROVIDER=gemini: it deletes each document's
chunks and re-runs the real pipeline (extract -> clean -> chunk -> embed ->
index) through app.ingestion.service.ingest_document, so statuses and chunk
metadata stay exactly as if the docs had been uploaded fresh.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database.base import Base, SessionLocal, engine  # noqa: E402
from app.logging_config import configure_logging, get_logger  # noqa: E402
from app.models import Document, DocumentChunk  # noqa: E402

configure_logging()
logger = get_logger("scripts.reindex_all")


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-index all documents")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without changing data")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        provider_name = settings.embedding_provider
        if provider_name == "gemini" and not settings.gemini_api_key:
            print("[FAIL] EMBEDDING_PROVIDER=gemini but GEMINI_API_KEY is empty.")
            print("       Set the key in .env (see GEMINI_SETUP.md), or use the hash provider.")
            return 1

        docs = db.query(Document).order_by(Document.id).all()
        if not docs:
            print("No documents found - seed first: python scripts/seed_data.py")
            return 1

        print("=" * 64)
        print(f"Re-indexing {len(docs)} document(s) with embedding provider: {provider_name}")
        print("=" * 64)

        if args.dry_run:
            for d in docs:
                n = db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
                print(f"  [dry-run] #{d.id} {d.name} (status={d.status}, chunks={n})")
            print("Dry run complete - no changes made. Drop --dry-run to execute.")
            return 0

        from app.ingestion.service import IngestionError, ingest_document

        ok = failed = 0
        for d in docs:
            try:
                doc = ingest_document(db, d.id)
                n = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
                model = (
                    db.query(DocumentChunk.embedding_model)
                    .filter(DocumentChunk.document_id == doc.id)
                    .first()
                )
                print(f"[OK]    #{doc.id} {doc.name} -> {n} chunks (embedding_model={model[0] if model else '?'})")
                ok += 1
            except (IngestionError, Exception) as exc:  # noqa: BLE001
                db.rollback()
                print(f"[FAIL]  #{d.id} {d.name}: {exc}")
                failed += 1

        print("-" * 64)
        print(f"Done. {ok} re-indexed, {failed} failed.")
        return 1 if failed else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
