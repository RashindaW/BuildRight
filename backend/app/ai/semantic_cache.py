"""Semantic answer cache — repeat questions stream instantly and cost $0.

Scope is deliberately conservative: only FIRST-TURN GUEST questions are cacheable
(no history, no user memory → the answer depends solely on the question + catalog).
A hit requires cosine ≥ 0.95 in the active embedding space, a fresh TTL, the same
catalog stamp — and, before serving, the cached text is RE-VALIDATED against the
items' CURRENT prices, so a stale price can never leak (guardrail invariance).

Backends: Redis when `redis_url` is configured (lazy import), else a bounded
in-process store — identical behavior, keyless tests use the in-memory path.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger("app.ai.semantic_cache")

_TTL_S = 3600
_MIN_SIM = 0.95
_MAX_ENTRIES = 200
_REDIS_KEY = "buildright:semcache"


@dataclass
class CacheEntry:
    question: str
    vec: list[float]
    text: str
    grounded_item_ids: list[str] = field(default_factory=list)
    catalog_stamp: str = ""
    created_at: float = 0.0


class _MemoryBackend:
    def __init__(self):
        self.entries: list[CacheEntry] = []

    def load(self) -> list[CacheEntry]:
        return self.entries

    def save(self, entries: list[CacheEntry]) -> None:
        self.entries = entries[-_MAX_ENTRIES:]


class _RedisBackend:  # pragma: no cover - exercised only with a live Redis
    def __init__(self, url: str):
        import redis
        self._r = redis.Redis.from_url(url, decode_responses=True)

    def load(self) -> list[CacheEntry]:
        raw = self._r.lrange(_REDIS_KEY, 0, _MAX_ENTRIES)
        return [CacheEntry(**json.loads(x)) for x in raw]

    def save(self, entries: list[CacheEntry]) -> None:
        pipe = self._r.pipeline()
        pipe.delete(_REDIS_KEY)
        for e in entries[-_MAX_ENTRIES:]:
            pipe.rpush(_REDIS_KEY, json.dumps(e.__dict__))
        pipe.expire(_REDIS_KEY, _TTL_S)
        pipe.execute()


_backend = None


def _get_backend():
    global _backend
    if _backend is None:
        url = getattr(settings, "redis_url", "") or ""
        if url:
            try:
                _backend = _RedisBackend(url)
            except Exception:  # noqa: BLE001 - Redis down → degrade to memory
                logger.warning("redis unavailable — semantic cache using in-memory backend")
                _backend = _MemoryBackend()
        else:
            _backend = _MemoryBackend()
    return _backend


def reset() -> None:
    """Test hook."""
    global _backend
    _backend = None


def _embed(text: str) -> list[float]:
    from app.ai.embeddings.provider import get_embedding_provider
    return get_embedding_provider().embed_query(text)


def _cosine(a: list[float], b: list[float]) -> float:
    import numpy as np
    va, vb = np.asarray(a), np.asarray(b)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na == 0 or nb == 0:
        return 0.0
    return float(va @ vb / (na * nb))


def _catalog_stamp(db) -> str:
    """Cheap catalog-version proxy: item count (admin adds/removes bust the cache)."""
    from sqlalchemy import func, select
    from app.models.menu import MenuItem
    try:
        n = db.execute(select(func.count(MenuItem.id))).scalar() or 0
        return str(n)
    except Exception:  # noqa: BLE001
        return "0"


def _revalidate(db, entry: CacheEntry) -> bool:
    """Cached prices must still match the CURRENT catalog before serving."""
    from sqlalchemy import select
    from app.ai.guardrails import validate_response
    from app.models.menu import MenuItem

    if not entry.grounded_item_ids:
        return validate_response(entry.text, [], allow_multiples=True).ok
    items = db.execute(
        select(MenuItem).where(
            (MenuItem.slug.in_(entry.grounded_item_ids)) | (MenuItem.id.in_(entry.grounded_item_ids))
        )
    ).scalars().all()
    grounded = [{"price": it.price_cents / 100} for it in items]
    return validate_response(entry.text, grounded, allow_multiples=True).ok


def lookup(db, question: str) -> CacheEntry | None:
    if not settings.semantic_cache_enabled:
        return None
    try:
        backend = _get_backend()
        now = time.time()
        stamp = _catalog_stamp(db)
        entries = [e for e in backend.load() if now - e.created_at < _TTL_S and e.catalog_stamp == stamp]
        if not entries:
            return None
        qv = _embed(question)
        best, best_sim = None, 0.0
        for e in entries:
            sim = _cosine(qv, e.vec)
            if sim > best_sim:
                best, best_sim = e, sim
        if best is None or best_sim < _MIN_SIM:
            return None
        if not _revalidate(db, best):
            logger.info('"semantic_cache_stale_price_evicted"')
            backend.save([e for e in entries if e is not best])
            return None
        logger.info('"semantic_cache_hit: sim=%.3f"', best_sim)
        return best
    except Exception:  # noqa: BLE001 - the cache must never break chat
        logger.exception("semantic cache lookup failed")
        return None


def store(db, question: str, text: str, grounded_item_ids: list[str]) -> None:
    if not settings.semantic_cache_enabled or not text:
        return
    try:
        backend = _get_backend()
        entries = backend.load()
        entries.append(CacheEntry(
            question=question,
            vec=_embed(question),
            text=text,
            grounded_item_ids=[i for i in grounded_item_ids if i][:12],
            catalog_stamp=_catalog_stamp(db),
            created_at=time.time(),
        ))
        backend.save(entries)
    except Exception:  # noqa: BLE001
        logger.exception("semantic cache store failed")
