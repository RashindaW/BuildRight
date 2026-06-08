"""Embedding provider abstraction.

FastEmbedProvider (default) uses BAAI/bge-small-en-v1.5 (384-dim) via fastembed.
It is offline, deterministic, and needs no API key — the model downloads once to
~/.cache/fastembed on first use.

HashEmbeddingProvider is a lightweight, download-free provider for unit tests.

Additional providers (OpenAI, Voyage) can implement the EmbeddingProvider Protocol
and be selected via settings.embedding_provider.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, runtime_checkable

from app.core.config import settings


@runtime_checkable
class EmbeddingProvider(Protocol):
    model_id: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class FastEmbedProvider:
    """Local ONNX embeddings via fastembed — no API key, runs offline."""

    model_id = "bge-small-en-v1.5"
    dim = 384

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or settings.embedding_model
        self._model = None  # lazy-load to avoid slow import at startup

    def _get_model(self):
        if self._model is None:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(self._model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        return [list(v) for v in model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        model = self._get_model()
        return list(next(iter(model.embed([text]))))


class HashEmbeddingProvider:
    """Deterministic unit-vector embeddings from content hash — no downloads.

    Not useful for semantic search, but produces reproducible vectors that
    exercise the full retrieval pipeline in tests without fastembed.
    """

    model_id = "hash-v1"
    dim = 384

    def _hash_to_unit_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        raw = [b / 255.0 - 0.5 for b in digest]
        # pad / truncate to self.dim
        while len(raw) < self.dim:
            raw = raw + raw
        raw = raw[:self.dim]
        magnitude = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / magnitude for x in raw]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_unit_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._hash_to_unit_vector(text)


_provider_instance: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return a singleton embedding provider selected by settings.embedding_provider."""
    global _provider_instance
    if _provider_instance is None:
        name = settings.embedding_provider
        if name == "fastembed":
            _provider_instance = FastEmbedProvider()
        elif name == "hash":
            _provider_instance = HashEmbeddingProvider()
        else:
            raise ValueError(f"Unknown embedding_provider: {name!r}")
    return _provider_instance
