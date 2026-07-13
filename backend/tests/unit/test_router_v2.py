"""Router v2: learned difficulty routing, constraint filter, and cascade escalation."""

from __future__ import annotations

import pytest

from app.ai import router, service
from app.ai.context import ToolContext
from app.ai.registry import registry
from app.ai.routing.difficulty import p_cheap_ok
from app.ai.routing.policy import decide, strongest_healthy
from app.core.config import settings


@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch):
    # Only the Claude entries are configured (no free-tier cloud keys).
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    registry.reload()
    yield
    registry.reload()


def test_difficulty_head_separates_easy_from_hard():
    easy = p_cheap_ok("Do you have cordless drills?")
    hard = p_cheap_ok("I want to paint my bedroom, it's 12 by 10 feet with 8 foot walls. What do I need?")
    assert easy > 0.5 > hard


def test_decide_routes_easy_cheap_and_hard_heavy():
    d_easy = decide("How much is the cheapest hammer?")
    assert d_easy is not None and d_easy.model_id == "claude-haiku-4-5"
    d_hard = decide("Compare corded vs cordless circular saws and plan a 10x12 deck build")
    assert d_hard is not None and d_hard.model_id == "claude-sonnet-4-6"
    assert d_hard.predicted_difficulty > d_easy.predicted_difficulty


def test_decide_vision_constraint():
    d = decide("what is this tool?", has_image=True)
    assert d is not None
    e = registry.get(d.model_id)
    assert "vision" in e.capabilities
    assert d.label == "multimodal"


def test_strongest_healthy_excludes_current():
    assert strongest_healthy(exclude="claude-haiku-4-5") == "claude-sonnet-4-6"
    assert strongest_healthy(exclude="claude-sonnet-4-6") == "claude-haiku-4-5"


@pytest.mark.asyncio
async def test_classify_turn_dispatches_to_v2():
    # v2 needs no client call at all — passing None proves it.
    label, model = await router.classify_turn(None, "Do you sell duct tape?")
    assert model == "claude-haiku-4-5" and label == "simple"


# ---- cascade: violation on cheap → visible retry on heavy ------------------

class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Usage:
    input_tokens, output_tokens = 3, 3


class _Resp:
    def __init__(self, text):
        self.stop_reason = "end_turn"
        self.content = [_Blk(type="text", text=text)]
        self.usage = _Usage()


@pytest.mark.asyncio
async def test_provider_failure_fails_over_to_healthy_model(monkeypatch):
    """A retryable provider failure mid-turn retries once on the strongest healthy
    model — and marks the dead one unhealthy so later turns route around it."""
    from app.ai.providers.base import ProviderConnectionError

    calls = {"n": 0}

    class _Msgs:
        async def create(self, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ProviderConnectionError("connection refused", provider="pool", model="claude-haiku-4-5")
            return _Resp("Here to help — what are you building today, if I may ask kindly?")

    class _Client:
        messages = _Msgs()

    async def _fake_classify(client, q, has_image=False, model=None):
        return ("simple", "claude-haiku-4-5")

    monkeypatch.setattr(service, "_get_async_client", lambda: _Client())
    monkeypatch.setattr(router, "classify_turn", _fake_classify)
    monkeypatch.setattr(service, "_build_executors", lambda: {})

    events = []
    async for ev in service.stream_chat([], ToolContext(menu=[], db=None), "hi there friend"):
        events.append(ev)

    done = events[-1]["data"]
    assert done["escalated"] is True
    assert done["model"] == "claude-sonnet-4-6"
    assert "building" in done["text"]
    assert registry.get("claude-haiku-4-5").healthy is False  # marked for future turns
    registry.mark_healthy("claude-haiku-4-5")


@pytest.mark.asyncio
async def test_cascade_escalates_violation_to_heavy(monkeypatch):
    answers = [
        _Resp("This beauty is only $499.99 today — trust me, a steal for the weekend."),  # cheap: fabricated
        _Resp("I couldn't find that exact item; happy to search for an alternative."),    # heavy: clean
    ]

    class _Msgs:
        async def create(self, **kw):
            return answers.pop(0)

    class _Client:
        messages = _Msgs()

    async def _fake_classify(client, q, has_image=False, model=None):
        return ("simple", "claude-haiku-4-5")

    monkeypatch.setattr(service, "_get_async_client", lambda: _Client())
    monkeypatch.setattr(router, "classify_turn", _fake_classify)
    monkeypatch.setattr(service, "_build_executors", lambda: {})
    monkeypatch.setattr(settings, "router_cascade_enabled", True)

    events = []
    async for ev in service.stream_chat([], ToolContext(menu=[], db=None), "price?"):
        events.append(ev)

    kinds = [e["event"] for e in events]
    esc = [e["data"] for e in events if e["event"] == "trace" and e["data"].get("type") == "escalation"]
    assert esc and esc[0]["from"] == "claude-haiku-4-5" and esc[0]["to"] == "claude-sonnet-4-6"
    assert "delta_reset" in kinds
    done = events[-1]["data"]
    assert done["escalated"] is True
    assert done["model"] == "claude-sonnet-4-6"
    assert "alternative" in done["text"]
    assert done["guardrail_violation"] is False  # the second opinion passed
    emitted = "".join(e["data"]["text"] for e in events if e["event"] == "delta")
    assert "$499.99" not in emitted
