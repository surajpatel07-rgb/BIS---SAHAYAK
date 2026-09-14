"""Seed development data: users + sample BIS-style PDFs (SAMPLE DATA).

Usage (from backend/):
    python ../scripts/seed_data.py

Creates:
- admin@bisbuddy.in / Admin@12345 (role=admin)
- demo@bisbuddy.in / Demo@12345  (role=user)
- All sample documents from data/sample_documents, fully ingested.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database.base import Base, SessionLocal, engine  # noqa: E402
from app.models import Document, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.logging_config import configure_logging  # noqa: E402

configure_logging()

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"

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

USERS = [
    {"name": "BIS Admin", "email": "admin@bisbuddy.in", "password": "Admin@12345", "role": "admin"},
    {"name": "Demo User", "email": "demo@bisbuddy.in", "password": "Demo@12345", "role": "user"},
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Users ---------------------------------------------------------------
        for spec in USERS:
            existing = db.query(User).filter(User.email == spec["email"]).first()
            if not existing:
                db.add(
                    User(
                        name=spec["name"],
                        email=spec["email"],
                        password_hash=hash_password(spec["password"]),
                        role=spec["role"],
                    )
                )
                print(f"user created: {spec['email']}")
            else:
                print(f"user exists:  {spec['email']}")
        db.commit()

        # Documents -----------------------------------------------------------
        from app.ingestion.service import ingest_document

        for spec in SAMPLE_DOCS:
            path = SAMPLE_DIR / spec["file"]
            if not path.exists():
                print(f"!! sample pdf missing, run scripts/build_sample_pdfs.py first: {path}")
                continue

            existing = db.query(Document).filter(Document.name == spec["name"]).first()
            if existing:
                print(f"doc exists:   {spec['name']} (status={existing.status})")
                continue

            import shutil

            dest = Path("data/uploads")
            dest.mkdir(parents=True, exist_ok=True)
            stored = dest / f"seed_{spec['file']}"
            shutil.copyfile(path, stored)

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
                print(f"doc indexed:  {spec['name']}")
            except Exception as exc:  # noqa: BLE001
                print(f"doc FAILED:   {spec['name']}: {exc}")
    finally:
        db.close()
    print("seed complete")


if __name__ == "__main__":
    seed()
