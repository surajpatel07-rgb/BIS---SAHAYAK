"""BIS Buddy FastAPI application."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse

from app.api import auth, chat, documents, misc, search
from app.config import settings
from app.logging_config import configure_logging, get_logger
from app.database.base import Base, engine

configure_logging()
logger = get_logger("app.main")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"  # backend/static


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables + run lightweight migrations on startup.
    from app.database.migrations import run_migrations

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)

    # First-run seeding (idempotent) — controlled by SEED_SAMPLE_DATA (default true).
    if settings.seed_sample_data:
        from app.database.base import SessionLocal
        from app.startup_seed import seed_if_empty

        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()

    logger.info(
        "BIS Buddy backend started (llm=%s, embeddings=%s, seeding=%s)",
        "gemini" if settings.llm_available else "fallback",
        settings.embedding_provider,
        "on" if settings.seed_sample_data else "off",
    )
    yield
    logger.info("BIS Buddy backend stopped")


app = FastAPI(
    title="BIS Buddy API",
    description="AI-powered assistant for Indian Standards & BIS services",
    version="1.0.0",
    lifespan=lifespan,
)

_origins = settings.cors_origin_list
if settings.cors_regex_or_none:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_regex_or_none,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS: regex mode enabled (%s)", settings.cors_regex_or_none)
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(misc.router)

_STATIC_READY = STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists()


# ---- Optional static frontend (single-service deploys) ----------------------
# If backend/static exists (deploy CI copies frontend/dist there), serve it.
# API routes, /docs and /health keep priority over the SPA catch-all.
if _STATIC_READY:
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith(("api/", "docs", "openapi.json", "health")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")  # SPA fallback

    logger.info("Serving frontend from %s", STATIC_DIR)
else:

    @app.get("/")
    def root():
        return {
            "app": "BIS Buddy API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }
