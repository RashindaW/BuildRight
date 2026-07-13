"""Semantic cache: hit/miss thresholds, stale-price re-validation, stream_chat wiring."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai import router, semantic_cache, service
from app.ai.context import ToolContext
from app.core.db import SessionLocal
from app.models.menu import MenuItem


@pytest.fixture(autouse=True)
def _fresh_cache():
    semantic_cache.reset()
    yield
    semantic_cache.reset()


def test_store_lookup_roundtrip_and_miss():
    db = SessionLocal()
    try:
        semantic_cache.store(db, "do you sell hammers", "Yes, we carry hammers.", [])
        hit = semantic_cache.lookup(db, "do you sell hammers")
        assert hit is not None and "hammers" in hit.text
        assert semantic_cache.lookup(db, "what is your return policy for gas tools") is None
    finally:
        db.close()


def test_stale_price_is_evicted_not_served():
    db = SessionLocal()
    try:
        item = db.execute(select(MenuItem).where(MenuItem.is_available.is_(True)).limit(1)).scalar_one()
        price = item.price_cents / 100
        semantic_cache.store(db, "how much is it", f"It costs ${price:.2f} today.", [item.slug])
        assert semantic_cache.lookup(db, "how much is it") is not None

        item.price_cents += 100  # price changed → cached text is now stale
        db.commit()
        try:
            assert semantic_cache.lookup(db, "how much is it") is None
        finally:
            item.price_cents -= 100
            db.commit()
    finally:
        db.close()


class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Usage:
    input_tokens, output_tokens = 5, 5


class _Resp:
    def __init__(self, text):
        self.stop_reason = "end_turn"
        self.content = [_Blk(type="text", text=text)]
        self.usage = _Usage()


@pytest.mark.asyncio
async def test_second_identical_guest_question_served_from_cache(monkeypatch):
    calls = {"n": 0}

    class _Msgs:
        async def create(self, **kw):
            calls["n"] += 1
            return _Resp("We stock several tarps, all ready for pickup today.")

    class _Client:
        messages = _Msgs()

    async def _fake_classify(client, q, has_image=False, model=None):
        return ("simple", "claude-haiku-4-5")

    monkeypatch.setattr(service, "_get_async_client", lambda: _Client())
    monkeypatch.setattr(router, "classify_turn", _fake_classify)
    monkeypatch.setattr(service, "_build_executors", lambda: {})

    db = SessionLocal()
    try:
        ctx = ToolContext(menu=[], db=db)  # guest: no user_id

        first = [ev async for ev in service.stream_chat([], ctx, "do you have tarps?")]
        assert first[-1]["data"]["text"].startswith("We stock")
        assert calls["n"] == 1

        second = [ev async for ev in service.stream_chat([], ctx, "do you have tarps?")]
        done = second[-1]["data"]
        assert calls["n"] == 1, "cache hit must not call the LLM"
        assert done["cache"] == "semantic" and done["cost_usd"] == 0.0
        assert done["text"] == first[-1]["data"]["text"]
        kinds = [(e["event"], e["data"].get("type")) for e in second]
        assert ("trace", "cache") in kinds
    finally:
        db.close()
