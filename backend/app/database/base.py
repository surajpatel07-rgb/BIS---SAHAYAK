"""SQLAlchemy engine and session management."""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import BASE_DIR, settings
from app.logging_config import get_logger

logger = get_logger("app.database")


def _resolve_sqlite_url(url: str) -> str:
    """Make relative sqlite paths absolute (independent of process CWD)."""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw = url[len(prefix):]
        if raw and not raw.startswith("/") and ":" not in raw[:3]:
            path = (BASE_DIR / raw).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            url = prefix + str(path).replace("\\", "/")
    return url


settings.database_url = _resolve_sqlite_url(settings.database_url)

if settings.database_url.startswith("sqlite"):
    engine_kwargs: dict = {
        "connect_args": {
            "check_same_thread": False,
            # Wait up to 30s for a locked DB instead of failing instantly —
            # concurrent chat requests write concurrently under WAL.
            "timeout": 30,
        }
    }
else:
    engine_kwargs = {"pool_pre_ping": True}

engine = create_engine(settings.database_url, **engine_kwargs)

# SQLite pragmas + ensure data dir exists
if settings.database_url.startswith("sqlite"):
    _db_file = settings.database_url.split("sqlite:///")[-1]
    _db_abs = Path(_db_file) if _db_file.startswith("/") else (BASE_DIR / _db_file)
    _db_abs.parent.mkdir(parents=True, exist_ok=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
