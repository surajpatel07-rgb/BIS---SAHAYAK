"""Lightweight idempotent migration runner.

Creates any tables missing via Base.metadata, then applies column-level
migrations guarded by existence checks. Works on SQLite and Postgres. For a
full Alembic setup, see README (deployment section).
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.logging_config import get_logger

logger = get_logger("app.database.migrations")


def _add_column(db, table: str, ddl: str, column: str) -> None:
    db.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    logger.info("migration: added %s.%s", table, column)


def run_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as db:
        # --- future column migrations go here -------------------------------
        # Example (idempotent):
        # if "documents" in inspector.get_table_names() and not any(
        #     c["name"] == "new_col" for c in inspector.get_columns("documents")
        # ):
        #     _add_column(db, "documents", "new_col VARCHAR(50) DEFAULT ''", "new_col")
        pass
    logger.info("migrations up to date")
