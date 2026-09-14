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
# ABSOLUTE: the backend process CWD may be backend/, so a relative path would
# scatter uploads into backend/data/uploads and break ingestion.
UPLOADS_DIR = BASE_DIR / "data" / "uploads"

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
        "category": "everyday_products",
        "subcategory": "Construction",
        "product_name": "Ordinary Portland Cement",
    },
    {
        "file": "sample_IS_3025_helmet_spec.pdf",
        "name": "IS 2925:2020 Industrial Safety Helmets (SAMPLE)",
        "standard_number": "IS 2925:2020",
        "title": "Industrial Safety Helmets — Specification (Sample)",
        "year": 2020,
        "document_type": "standard",
        "category": "everyday_products",
        "subcategory": "Safety",
        "product_name": "Industrial Safety Helmets",
    },
    {
        "file": "sample_bis_consumer_guide.pdf",
        "name": "BIS Consumer Guide — Understanding the ISI Mark (SAMPLE)",
        "standard_number": "CONSUMER-GUIDE",
        "title": "Understanding the ISI Mark — A Consumer Guide (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "general_bis",
        "subcategory": "Consumer Awareness",
        "product_name": "",
    },
    {
        "file": "sample_bis_certification_process.pdf",
        "name": "BIS Product Certification Process for Manufacturers (SAMPLE)",
        "standard_number": "BIS-PROCESS",
        "title": "BIS Product Certification — Process Guide for Manufacturers (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "industry",
        "subcategory": "Certification",
        "product_name": "",
    },
    {
        "file": "sample_food_packaged_drinking_water.pdf",
        "name": "Food Safety Guide — Packaged Drinking Water & BIS (SAMPLE)",
        "standard_number": "FOOD-WATER-GUIDE",
        "title": "Packaged Drinking Water and BIS Certification — Consumer Guide (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "food",
        "subcategory": "Water",
        "product_name": "Packaged Drinking Water",
    },
    {
        "file": "sample_hallmarking_huid_guide.pdf",
        "name": "Gold & Silver Hallmarking — HUID Consumer Guide (SAMPLE)",
        "standard_number": "HALLMARK-GUIDE",
        "title": "Understanding BIS Hallmarking, HUID and Fineness — Consumer Guide (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "hallmarking",
        "subcategory": "Hallmarking",
        "product_name": "Gold Jewellery Hallmarking",
    },
    {
        "file": "sample_electronics_electrical_guide.pdf",
        "name": "Electronics & Electrical Products — BIS Marks Guide (SAMPLE)",
        "standard_number": "ELEC-GUIDE",
        "title": "BIS Certification Marks on Electronics and Electrical Products — Consumer Guide (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "electronics_electrical",
        "subcategory": "Appliances",
        "product_name": "",
    },
    {
        "file": "sample_everyday_products_guide.pdf",
        "name": "Everyday Products — ISI Mark Buying Guide (SAMPLE)",
        "standard_number": "EVERYDAY-GUIDE",
        "title": "ISI Mark Buying Guide for Everyday Household Products (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "everyday_products",
        "subcategory": "Household",
        "product_name": "",
    },
    {
        "file": "sample_general_bis_overview.pdf",
        "name": "About BIS — Indian Standards, Marks and Consumer Services (SAMPLE)",
        "standard_number": "BIS-OVERVIEW",
        "title": "About the Bureau of Indian Standards — Overview for Consumers and Industry (Sample)",
        "year": 2024,
        "document_type": "guide",
        "category": "general_bis",
        "subcategory": "Overview",
        "product_name": "",
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

            dest = UPLOADS_DIR
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
                subcategory=spec.get("subcategory", ""),
                product_name=spec.get("product_name", ""),
                description=f"Sample BIS-style document for development. {spec['title']}",
                file_path=str(dest / stored.name),
                file_size=stored.stat().st_size,
                source_url="",
                # Demo provenance — the UI shows a DEMO DATA badge for these.
                source_name="BIS Buddy Demo Corpus",
                source_type="demo",
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
