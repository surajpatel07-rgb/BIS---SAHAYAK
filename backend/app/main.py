"""BIS Buddy FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, documents, misc, search
from app.config import settings
from app.logging_config import configure_logging, get_logger
from app.database.base import Base, engine

configure_logging()
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience). Production should use Alembic;
    # see backend/app/database/migrations.py for the lightweight migration runner.
    from app.database.migrations import run_migrations

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    logger.info("BIS Buddy backend started (llm=%s, embeddings=%s)",
                "gemini" if settings.llm_available else "fallback",
                settings.embedding_provider)
    yield
    logger.info("BIS Buddy backend stopped")


app = FastAPI(
    title="BIS Buddy API",
    description="AI-powered assistant for Indian Standards & BIS services",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(misc.router)


@app.get("/")
def root():
    return {
        "app": "BIS Buddy API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
