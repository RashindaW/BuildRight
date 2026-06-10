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
    """Deterministic, download-free embeddings via signed feature hashing of tokens
    (a hashing bag-of-words / hashing-vectorizer).

    Unlike a whole-string hash, this places each token into a dimension by hash, so
    documents that share words get similar vectors — the vector arm becomes a real
    (lexical-semantic) signal rather than noise. It does not capture neural semantics
    (synonyms/intent) like fastembed, but it is reproducible and needs no model
    download, making it a sensible offline fallback when onnxruntime is unavailable.
    """

    model_id = "hash-bow-v1"
    dim = 384

    @staticmethod
    def _tokens(text: str) -> list[str]:
        out, cur = [], []
        for ch in text.lower():
            if ch.isalnum():
                cur.append(ch)
            elif cur:
                out.append("".join(cur))
                cur = []
        if cur:
            out.append("".join(cur))
        return [t for t in out if len(t) >= 2]

    def _bow_vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in self._tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if ((h >> 9) & 1) else -1.0
            vec[idx] += sign
        magnitude = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / magnitude for x in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._bow_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._bow_vector(text)


_provider_instance: EmbeddingProvider | None = None


import logging

logger = logging.getLogger("app.ai.embeddings.provider")


def _fastembed_loadable() -> bool:
    """True if fastembed (and its onnxruntime backend) can actually import on this host."""
    try:
        import fastembed  # noqa: F401
        return True
    except Exception as e:  # ImportError, or onnxruntime DLL init failure
        logger.warning(
            "fastembed unavailable (%s: %s) — falling back to the deterministic 'hash' "
            "embedding provider. Semantic vector search is reduced until a host where "
            "fastembed/onnxruntime loads is used (no code change needed there).",
            type(e).__name__, e,
        )
        return False


def get_embedding_provider() -> EmbeddingProvider:
    """Return a singleton embedding provider selected by settings.embedding_provider.

    The default 'fastembed' gracefully falls back to 'hash' if fastembed/onnxruntime
    can't load on this host, so the RAG pipeline always has a populated vector arm and
    the app runs anywhere. Set EMBEDDING_PROVIDER=hash to force the offline fallback.
    """
    global _provider_instance
    if _provider_instance is None:
        name = settings.embedding_provider
        if name == "fastembed":
            _provider_instance = FastEmbedProvider() if _fastembed_loadable() else HashEmbeddingProvider()
        elif name == "hash":
            _provider_instance = HashEmbeddingProvider()
        else:
            raise ValueError(f"Unknown embedding_provider: {name!r}")
    return _provider_instance
