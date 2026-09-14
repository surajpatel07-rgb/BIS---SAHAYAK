"""Verify the Gemini configuration used by BIS Buddy.

Run from the project root:
    python scripts/check_gemini.py

Checks, in order:
1. Where the .env file was found and which provider is selected.
2. GEMINI_API_KEY present (from .env or real environment).
3. The key WORKS for embeddings  (gemini-embedding-001, RETRIEVAL_QUERY).
4. The key WORKS for chat        (GEMINI_MODEL, one tiny generation).

Exit code 0 = everything configured and reachable; 1 = something is missing.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.logging_config import configure_logging, get_logger  # noqa: E402

configure_logging()
logger = get_logger("scripts.check_gemini")

OK, BAD, WARN = "[OK]  ", "[FAIL]", "[WARN]"
failures = 0


def say(tag: str, msg: str) -> None:
    print(f"{tag} {msg}")


print("=" * 64)
print("BIS Buddy - Gemini configuration check")
print("=" * 64)

# 1) env file + providers -----------------------------------------------------
print(f"{OK} .env file: {settings.env_file_in_use}")
print(f"      embedding provider: {settings.embedding_provider}")
print(f"      llm model:          {settings.gemini_model}")

if settings.embedding_provider != "gemini":
    say(WARN, "EMBEDDING_PROVIDER is not 'gemini' - set EMBEDDING_PROVIDER=gemini in .env")
    failures += 1

# 2) key present --------------------------------------------------------------
if not settings.gemini_api_key:
    say(BAD, "GEMINI_API_KEY is not set. Add it to .env (see GEMINI_SETUP.md).")
    print("      Get a free key at: https://aistudio.google.com/apikey")
    sys.exit(1)
masked = settings.gemini_api_key[:6] + "..." + settings.gemini_api_key[-4:]
say(OK, f"GEMINI_API_KEY found ({masked})")

# 3) embeddings work ----------------------------------------------------------
print(f"\nTesting embeddings endpoint ({settings.gemini_embedding_model})...")
try:
    from app.rag.embeddings import get_embedding_provider

    provider = get_embedding_provider(validate=True)
    vec = provider.embed_query("cement standard requirements")
    say(OK, f"Embeddings OK - provider={provider.name}, dim={len(vec)}")
    if provider.name != "gemini":
        say(BAD, "Fell back to the hash provider - key was rejected.")
        failures += 1
except Exception as exc:  # noqa: BLE001
    say(BAD, f"Embeddings failed: {exc}")
    failures += 1

# 4) chat works ---------------------------------------------------------------
print(f"\nTesting chat endpoint ({settings.gemini_model})...")
try:
    from app.rag.llm import GeminiLLMProvider

    llm = GeminiLLMProvider()
    reply = llm.generate("Reply with exactly one word: READY")
    say(OK, f"Chat OK - model replied: {reply.strip()[:40]!r}")
except Exception as exc:  # noqa: BLE001
    say(BAD, f"Chat failed: {exc}")
    failures += 1

print()
if failures:
    print(f"RESULT: {failures} problem(s) found. Fix .env and re-run this script.")
    sys.exit(1)
print("RESULT: Gemini is fully configured - embeddings and chat both work.")
print("Next: python scripts/reindex_all.py  (re-embed the corpus with Gemini)")
