"""Idempotent first-run seeding for fresh deployments.

Runs during app startup when SEED_SAMPLE_DATA=true (the default). It only
creates data that is MISSING — existing users/documents/chunks are never
modified or duplicated — so it is safe on every boot (Render free tier
recycles instances and often starts with an empty disk).

All documents created here are synthetic SAMPLE DATA, clearly labeled as such
(see scripts/build_sample_pdfs.py). They are NOT official BIS documents.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from app.logging_config import configure_logging, get_logger
from app.models import Document, User
from app.security import hash_password

configure_logging()
logger = get_logger("app.startup_seed")

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root
SAMPLE_DIR = BASE_DIR / "data" / "sample_documents"

USERS = [
    {"name": "BIS Admin", "email": "admin@bisbuddy.in", "password": "Admin@12345", "role": "admin"},
    {"name": "Demo User", "email": "demo@bisbuddy.in", "password": "Demo@12345", "role": "user"},
]

SAMPLE_DOCS = [
    {
        "file": "sample_IS_1234_cement_spec.pdf",
        "name": "IS 1234:2020 Portland Cement — Specification (SAMPLE)",
        "standard_number": "IS 1234:2020",
        "title": "Ordinary Portland Cement — Specification (Sample)",
        "year": 2020,
        "document_type": "standard",
        "category": "cement",
    },
    {
        "file": "sample_IS_3025_helmet_spec.pdf",
        "name": "IS 2925:2020 Industrial Safety Helmets (SAMPLE)",
        "standard_number": "IS 2925:2020",
        "title": "Industrial Safety Helmets — Specification (Sample)",
        "year": 2020,
        "document_type": "standard",
        "category": "safety",
    },
    {
        "file": "sample_bis_consumer_guide.pdf",
        "name": "BIS Consumer Guide — Understanding the ISI Mark (SAMPLE)",
        "standard_number": "CONSUMER-GUIDE",
        "title": "Understanding the ISI Mark — A Consumer Guide (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "consumer",
    },
    {
        "file": "sample_bis_certification_process.pdf",
        "name": "BIS Product Certification Process for Manufacturers (SAMPLE)",
        "standard_number": "BIS-PROCESS",
        "title": "BIS Product Certification — Process Guide for Manufacturers (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "certification",
    },
]


def seed_if_empty(db) -> None:  # noqa: ANN001 - SQLAlchemy Session
    """Create missing demo users and ingest missing SAMPLE documents.

    Never raises: a seeding failure is logged and swallowed so the API still
    boots (admin can upload/reseed manually through the UI).
    """
    try:
        # Users ---------------------------------------------------------------
        for spec in USERS:
            if not db.query(User).filter(User.email == spec["email"]).first():
                db.add(
                    User(
                        name=spec["name"],
                        email=spec["email"],
                        password_hash=hash_password(spec["password"]),
                        role=spec["role"],
                    )
                )
                logger.info("seeded user %s", spec["email"])
        db.commit()

        # Documents -----------------------------------------------------------
        from app.ingestion.service import ingest_document

        for spec in SAMPLE_DOCS:
            if db.query(Document).filter(Document.name == spec["name"]).first():
                continue
            src = SAMPLE_DIR / spec["file"]
            if not src.exists():
                logger.warning("sample PDF missing, skipping %s: %s", spec["name"], src)
                continue

            dest = Path("data/uploads")
            dest.mkdir(parents=True, exist_ok=True)
            stored = dest / f"seed_{spec['file']}"
            shutil.copyfile(src, stored)

            doc = Document(
                name=spec["name"],
                standard_number=spec["standard_number"],
                title=spec["title"],
                year=spec["year"],
                document_type=spec["document_type"],
                category=spec["category"],
                description=f"Sample BIS-style document for development. {spec['title']}",
                file_path=str(dest / stored.name),
                file_size=stored.stat().st_size,
                source_url="",
                status="uploaded",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            try:
                ingest_document(db, doc.id)
                logger.info("seeded + indexed %s", spec["name"])
            except Exception as exc:  # noqa: BLE001 - keep booting on failure
                logger.error("seeding failed for %s: %s", spec["name"], exc)
    except Exception:  # noqa: BLE001 - seeding must never block startup
        logger.exception("startup seeding failed; continuing with empty database")
        db.rollback()
