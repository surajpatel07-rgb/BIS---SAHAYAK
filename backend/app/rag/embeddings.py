"""Embedding providers with a clean provider abstraction.

Providers:
- HashEmbeddingProvider: deterministic local hashing-trick embeddings (no network).
  Works offline for dev/CI; decent lexical similarity, not semantic.
- GeminiEmbeddingProvider: Google text-embedding-004 via google-genai SDK.
"""
from __future__ import annotations

import hashlib
import math
import re

import numpy as np

from app.config import (
    EMBEDDING_PROVIDER_GEMINI,
    EMBEDDING_PROVIDER_HASH,
    settings,
)
from app.logging_config import get_logger

logger = get_logger("app.rag.embeddings")


class EmbeddingProvider:
    """Interface for embedding providers."""

    name: str = "base"
    dim: int = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embeddings via the hashing trick with word n-grams.

    Not semantic like a neural model, but stable, fast, dependency-free and
    good enough to exercise the whole RAG pipeline in dev/CI without API keys.
    """

    name = "hash"
    dim = settings.embedding_dim

    def _tokens(self, text: str) -> list[str]:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        words = text.split()
        # unigrams + bigrams improves matching quality for technical text
        grams = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
        return grams

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = self._tokens(text)
        if not tokens:
            return vec.tolist()
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 64) & 1 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embeddings (models/text-embedding-004)."""

    name = "gemini"
    dim = settings.embedding_dim

    def __init__(self) -> None:
        from google import genai  # imported lazily

        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        # The SDK accepts batches; keep batches small to be gentle on quotas.
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            resp = self._client.models.embed_content(
                model=self._model,
                contents=batch,
                config={
                    "task_type": "RETRIEVAL_DOCUMENT",
                    "output_dimensionality": settings.embedding_dim,
                },
            )
            out.extend([list(e.values) for e in resp.embeddings])
        return out

    def embed_query(self, text: str) -> list[float]:
        resp = self._client.models.embed_content(
            model=self._model,
            contents=[text],
            config={
                "task_type": "RETRIEVAL_QUERY",
                "output_dimensionality": settings.embedding_dim,
            },
        )
        return list(resp.embeddings[0].values)

    def validate_key(self) -> None:
        """Probe the API with a tiny embed to surface auth/quota errors early."""
        try:
            self.embed_query("connection test")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Gemini embeddings rejected the key: {exc}") from exc


def get_embedding_provider(validate: bool = False) -> EmbeddingProvider:
    if settings.embedding_provider == EMBEDDING_PROVIDER_GEMINI and settings.gemini_api_key:
        try:
            provider: EmbeddingProvider = GeminiEmbeddingProvider()
            if validate:
                provider.validate_key()
            return provider
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini embeddings unavailable (%s); using hash fallback", exc)
    return HashEmbeddingProvider()
