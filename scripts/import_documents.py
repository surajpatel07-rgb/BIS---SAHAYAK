"""Import knowledge documents into the BIS Buddy knowledge base.

Scans data/<category>/ folders (or takes explicit paths + metadata), ingests
each PDF through the REAL pipeline (extract -> clean -> chunk -> embed ->
index) and records full provenance metadata.

Folder -> category mapping (auto-detect):
    data/food/               -> food
    data/hallmarking/        -> hallmarking
    data/electronics/        -> electronics_electrical
    data/everyday_products/  -> everyday_products
    data/general_bis/        -> general_bis
    data/industry/           -> industry

Usage:
    python scripts/import_documents.py                    # import all folders
    python scripts/import_documents.py --category food    # one folder
    python scripts/import_documents.py --file path.pdf --category hallmarking \
        --source-url https://... --source-name "Bureau of Indian Standards" \
        --source-type official_bis --standard-number "IS 1417" --year 2022

The folder scan also reads optional sidecar JSON files: a PDF named
doc.pdf can have doc.json next to it with {"title": ..., "standard_number":
..., "source_url": ..., ...} to attach rich metadata.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.database.base import Base, SessionLocal, engine  # noqa: E402
from app.database.migrations import run_migrations  # noqa: E402
from app.ingestion.service import IngestionError, ingest_document, validate_pdf  # noqa: E402
from app.logging_config import configure_logging  # noqa: E402
from app.models import Document  # noqa: E402

configure_logging()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

FOLDER_CATEGORIES = {
    "food": "food",
    "hallmarking": "hallmarking",
    "electronics": "electronics_electrical",
    "electronics_electrical": "electronics_electrical",
    "everyday_products": "everyday_products",
    "everyday": "everyday_products",
    "general_bis": "general_bis",
    "general": "general_bis",
    "industry": "industry",
}

VALID_SOURCE_TYPES = {"official_bis", "government", "official", "demo"}


def _sidecar(pdf_path: Path) -> dict:
    js = pdf_path.with_suffix(".json")
    if js.exists():
        try:
            return json.loads(js.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  ! invalid JSON sidecar for {pdf_path.name}, ignoring")
    return {}


def import_file(
    db,
    pdf_path: Path,
    category: str,
    meta: dict,
    defaults: dict,
) -> Document | None:
    """Import one PDF; returns the Document row or None when skipped/failed."""
    from app.knowledge.registry import normalize_category

    content = pdf_path.read_bytes()
    try:
        validate_pdf(pdf_path.name, content)
    except IngestionError as exc:
        print(f"  ! SKIP {pdf_path.name}: {exc}")
        return None

    # skip if the same file was already imported (name + size match)
    existing = (
        db.query(Document)
        .filter(Document.name == meta.get("name", pdf_path.name))
        .filter(Document.file_size == len(content))
        .first()
    )
    if existing:
        print(f"  = already imported: {pdf_path.name} (doc {existing.id})")
        return existing

    uploads = DATA_DIR / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    import secrets

    stored = uploads / f"{secrets.token_hex(8)}_{pdf_path.stem}{pdf_path.suffix}"
    stored.write_bytes(content)

    doc = Document(
        name=meta.get("name", pdf_path.name),
        standard_number=meta.get("standard_number", defaults.get("standard_number", "")),
        title=meta.get("title", pdf_path.stem.replace("_", " ")),
        year=meta.get("year", defaults.get("year")),
        document_type=meta.get("document_type", defaults.get("document_type", "standard")),
        category=normalize_category(meta.get("category", category)),
        subcategory=meta.get("subcategory", ""),
        product_name=meta.get("product_name", ""),
        language=meta.get("language", "en"),
        description=meta.get("description", ""),
        file_path=str(stored),
        file_size=len(content),
        source_url=meta.get("source_url", defaults.get("source_url", "")),
        source_name=meta.get("source_name", defaults.get("source_name", "")),
        source_type=meta.get("source_type", defaults.get("source_type", "demo")),
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    try:
        ingest_document(db, doc.id)
        print(f"  + indexed: {pdf_path.name} -> {doc.category} (doc {doc.id})")
        return doc
    except IngestionError as exc:
        print(f"  ! FAILED {pdf_path.name}: {exc}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Import knowledge documents")
    ap.add_argument("--category", help="restrict to one category folder")
    ap.add_argument("--file", help="import a single PDF file")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--source-name", default="")
    ap.add_argument("--source-type", default="demo", choices=sorted(VALID_SOURCE_TYPES))
    ap.add_argument("--standard-number", default="")
    ap.add_argument("--year", type=int)
    args = ap.parse_args()

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    db = SessionLocal()

    defaults = {
        "source_url": args.source_url,
        "source_name": args.source_name,
        "source_type": args.source_type,
        "standard_number": args.standard_number,
        "year": args.year,
    }

    if args.file:
        pdf = Path(args.file)
        if not pdf.exists():
            print(f"file not found: {pdf}")
            return 1
        cat = args.category or "general_bis"
        import_file(db, pdf, cat, _sidecar(pdf), defaults)
        return 0

    total = ok = failed = skipped = 0
    for folder, category in sorted(FOLDER_CATEGORIES.items()):
        d = DATA_DIR / folder
        if not d.is_dir():
            continue
        if args.category and category != args.category:
            continue
        pdfs = sorted(d.glob("*.pdf"))
        if not pdfs:
            continue
        print(f"[{category}] <- data/{folder}/ ({len(pdfs)} file(s))")
        for pdf in pdfs:
            total += 1
            before = ok
            res = import_file(db, pdf, category, _sidecar(pdf), defaults)
            if res and res.status == "indexed":
                ok += 1
            elif res is None or res.status == "failed":
                if res is None:
                    skipped += 1
                else:
                    failed += 1
            del before

    print(f"\nDone: {ok} indexed, {failed} failed, {skipped} skipped of {total} file(s)")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
