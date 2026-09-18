"""Lightweight idempotent migration runner.

Creates any tables missing via Base.metadata, then applies column-level
migrations guarded by existence checks. Works on SQLite and Postgres. For a
full Alembic setup, see README (deployment section).

Knowledge-base expansion migrations:
- documents: category (normalized), subcategory, product_name, language,
  source_name, source_type columns; legacy category values remapped.
- product_categories / products / knowledge_sources / standard_metadata
  tables; registry rows seeded.
"""
from __future__ import annotations

import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.logging_config import get_logger

logger = get_logger("app.database.migrations")


def _add_column(db, table: str, ddl: str, column: str) -> None:
    db.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    logger.info("migration: added %s.%s", table, column)


# Legacy free-form category values -> canonical registry keys.
# Keys not listed here fall through to the registry's normalize_category.
_LEGACY_MAP = {
    "cement": "everyday_products",
    "safety": "everyday_products",
    "consumer": "general_bis",
    "certification": "industry",
    "general": "general_bis",
    "food": "food",
    "water": "water",
    "packaging": "packaging",
    "construction": "construction",
    "hallmarking": "hallmarking",
    "gold_silver": "hallmarking",
    "electronics_electrical": "electronics_electrical",
    "electronics": "electronics_electrical",
    "everyday_products": "everyday_products",
    "household": "everyday_products",
    "consumer_products": "everyday_products",
    "industry": "industry",
    "general_bis": "general_bis",
}


def _norm(raw: str | None) -> str:
    v = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    if v in _LEGACY_MAP:
        return _LEGACY_MAP[v]
    # Anything else delegates to the registry (covers new canonical keys like
    # water / packaging / construction automatically).
    from app.knowledge.registry import normalize_category

    return normalize_category(v)


def _sync_registry_tables(engine: Engine) -> None:
    """Create/refresh ProductCategory rows and registry Product rows.

    Registry products are keyed by name: existing rows are updated, missing
    rows inserted, admin-created rows (origin='admin') left untouched.
    """
    from sqlalchemy.orm import Session

    from app.knowledge.registry import CATEGORIES, PRODUCTS
    from app.models import Product as ProductRow
    from app.models import ProductCategory, StandardMetadata

    session = Session(bind=engine)
    try:
        for key, cat in CATEGORIES.items():
            existing = session.query(ProductCategory).filter(ProductCategory.key == key).first()
            if not existing:
                session.add(
                    ProductCategory(
                        key=key, label=cat.label, emoji=cat.emoji, description=cat.description
                    )
                    )
            else:
                existing.label = cat.label
                existing.emoji = cat.emoji
                existing.description = cat.description

        for p in PRODUCTS:
            row = session.query(ProductRow).filter(ProductRow.name == p.name).first()
            if not row:
                session.add(
                    ProductRow(
                        name=p.name,
                        category=p.category,
                        subcategory=p.subcategory,
                        standard_number=p.standard_number,
                        standard_title=p.standard_title,
                        certification_status=p.certification_status,
                        scheme=p.scheme,
                        checklist_json=list(p.consumer_checklist) or None,
                        notes=p.notes,
                        origin="registry",
                    )
                )
            else:
                row.category = p.category
                row.subcategory = p.subcategory
                row.standard_number = p.standard_number
                row.standard_title = p.standard_title
                row.certification_status = p.certification_status
                row.scheme = p.scheme
                row.checklist_json = list(p.consumer_checklist) or None
                row.notes = p.notes

        # Standard metadata catalog from registry products with known numbers
        for p in PRODUCTS:
            if p.standard_number:
                existing = (
                    session.query(StandardMetadata)
                    .filter(StandardMetadata.standard_number == p.standard_number)
                    .first()
                )
                if not existing:
                    session.add(
                        StandardMetadata(
                            standard_number=p.standard_number,
                            title=p.standard_title,
                            category=p.category,
                            product_name=p.name,
                        )
                    )

        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as db:
        # --- documents table: new knowledge-base columns ----------------------
        if "documents" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("documents")}
            if "subcategory" not in cols:
                _add_column(db, "documents", "subcategory VARCHAR(200) DEFAULT ''", "subcategory")
            if "product_name" not in cols:
                _add_column(db, "documents", "product_name VARCHAR(300) DEFAULT ''", "product_name")
            if "language" not in cols:
                _add_column(db, "documents", "language VARCHAR(20) DEFAULT 'en'", "language")
            if "source_name" not in cols:
                _add_column(db, "documents", "source_name VARCHAR(300) DEFAULT ''", "source_name")
            if "source_type" not in cols:
                _add_column(db, "documents", "source_type VARCHAR(30) DEFAULT 'demo'", "source_type")

            # Normalize legacy category values (cement/safety/consumer/...).
            rows = db.execute(text("SELECT DISTINCT category FROM documents")).fetchall()
            for (raw,) in rows:
                target = _norm(raw)
                if raw != target:
                    db.execute(
                        text("UPDATE documents SET category = :t WHERE category = :r"),
                        {"t": target, "r": raw},
                    )
                    logger.info("migration: category %r -> %r", raw, target)

    # --- new knowledge tables (idempotent) -----------------------------------
    # create_all only creates missing tables; existing data is never touched.
    from app.database.base import Base

    Base.metadata.create_all(bind=engine)

    _sync_registry_tables(engine)

    logger.info("migrations up to date")
