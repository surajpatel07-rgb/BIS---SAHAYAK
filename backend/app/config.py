"""Application settings loaded from environment / .env (pydantic-settings)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root

LLM_PROVIDER_GEMINI = "gemini"
LLM_PROVIDER_FALLBACK = "fallback"
EMBEDDING_PROVIDER_GEMINI = "gemini"
EMBEDDING_PROVIDER_HASH = "hash"


class Settings(BaseSettings):
    """Central typed configuration. All values come from env or .env."""

    model_config = SettingsConfigDict(
        # Accept the .env file at project root OR inside backend/ — whichever exists.
        # Earlier entries win; real environment variables always win over files.
        env_file=(str(BASE_DIR / ".env"), str(BASE_DIR / "backend" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Security
    secret_key: str = "dev-insecure-secret-change-me"
    access_token_expire_minutes: int = 10080  # 7 days

    # Database
    database_url: str = "sqlite:///./data/bisbuddy.db"

    # LLM
    gemini_api_key: str = ""
    # gemini-3.1-flash-lite: non-thinking, generous free tier — best demo default.
    # gemini-3.6-flash is higher quality but THINKS (needs a big token budget) and
    # its free tier allows only ~20 requests/day; better with a paid key.
    gemini_model: str = "gemini-3.1-flash-lite"
    # Thinking models (gemini-3.x) spend part of this budget on thoughts, so it
    # must be well above the desired answer length or answers get truncated.
    gemini_max_output_tokens: int = 8192

    # Embeddings
    embedding_provider: str = EMBEDDING_PROVIDER_HASH  # gemini | hash
    embedding_dim: int = 768
    gemini_embedding_model: str = "models/gemini-embedding-001"

    # Retrieval
    chunk_size: int = 900
    chunk_overlap: int = 150
    retrieval_top_k: int = 12
    rerank_top_n: int = 5
    min_relevance_score: float = 0.08
    retrieval_mode: str = "hybrid"  # lexical | hybrid

    # Ingestion
    max_upload_mb: int = 25

    # AI Product Identifier (vision). Uses the same GEMINI_API_KEY as chat.
    vision_max_image_mb: int = 8
    vision_target_edge: int = 1024

    # First-run seeding (creates demo users + SAMPLE documents when the DB is empty)
    seed_sample_data: bool = True

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.1:5173"
    # Optional regex allowing any <random>.onrender.com / *.vercel.app origin
    # (leave empty in dev; set e.g. "https://.*\.onrender\.com" on Render)
    cors_allow_regex: str = ""

    # App
    log_level: str = "INFO"
    data_dir: str = "./data"

    # Helpers ------------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_regex_or_none(self) -> str | None:
        return self.cors_allow_regex.strip() or None

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        if not p.is_absolute():
            p = (BASE_DIR / self.data_dir).resolve()
        return p

    @property
    def uploads_path(self) -> Path:
        p = self.data_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def llm_available(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def env_file_in_use(self) -> str:
        """Which .env file was actually found (for diagnostics)."""
        for candidate in (BASE_DIR / ".env", BASE_DIR / "backend" / ".env"):
            if candidate.exists():
                return str(candidate)
        return "(no .env file found - using real environment variables only)"

    @property
    def gemini_client_ready(self) -> bool:
        return self.llm_available


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
