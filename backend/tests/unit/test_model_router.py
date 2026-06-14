"""Model-router classification tests (keyless — heuristic paths don't call the API)."""

from __future__ import annotations

import pytest

from app.ai import router
from app.core.config import settings


class _FakeBlock:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class _FakeResp:
    def __init__(self, text: str):
        self.content = [_FakeBlock(text)]


class _FakeClient:
    """Records whether the classifier round-trip happened, returns a canned label."""

    def __init__(self, label: str = "SIMPLE"):
        self.label = label
        self.calls = 0

        class _Messages:
            async def create(_self, **kwargs):
                self.calls += 1
                return _FakeResp(self.label)

        self.messages = _Messages()


@pytest.mark.asyncio
async def test_image_always_escalates_without_classifier_call():
    client = _FakeClient()
    label, model = await router.classify_turn(client, "what is this?", has_image=True)
    assert label == router.MULTIMODAL
    assert model == settings.llm_model_heavy
    assert client.calls == 0  # vision short-circuits


@pytest.mark.asyncio
async def test_project_language_escalates_via_heuristic():
    client = _FakeClient()
    label, model = await router.classify_turn(client, "I want to repair my bedroom walls")
    assert label == router.COMPLEX
    assert model == settings.llm_model_heavy
    assert client.calls == 0  # heuristic fast-path, no round-trip


@pytest.mark.asyncio
async def test_short_message_stays_cheap_without_call():
    client = _FakeClient()
    label, model = await router.classify_turn(client, "drills?")
    assert label == router.SIMPLE
    assert model == settings.llm_model
    assert client.calls == 0


@pytest.mark.asyncio
async def test_ambiguous_message_uses_classifier_simple():
    client = _FakeClient(label="SIMPLE")
    label, model = await router.classify_turn(
        client, "do you carry exterior latex in a satin finish?"
    )
    assert label == router.SIMPLE
    assert model == settings.llm_model
    assert client.calls == 1  # classifier consulted


@pytest.mark.asyncio
async def test_ambiguous_message_classified_complex():
    client = _FakeClient(label="COMPLEX")
    label, model = await router.classify_turn(
        client, "compare every cordless drill you stock and tell me the best value"
    )
    assert label == router.COMPLEX
    assert model == settings.llm_model_heavy
    assert client.calls == 1


@pytest.mark.asyncio
async def test_classifier_failure_is_failsafe_cheap(monkeypatch):
    import anthropic

    class _BoomClient:
        class messages:
            @staticmethod
            async def create(**kwargs):
                raise anthropic.APIConnectionError(request=None)

    label, model = await router.classify_turn(
        _BoomClient(), "do you carry exterior latex in a satin finish?"
    )
    assert label == router.SIMPLE
    assert model == settings.llm_model


@pytest.mark.asyncio
async def test_router_disabled_pins_cheap_model(monkeypatch):
    monkeypatch.setattr(settings, "model_router_enabled", False)
    client = _FakeClient(label="COMPLEX")
    label, model = await router.classify_turn(client, "I want to repair my room")
    assert label == router.SIMPLE
    assert model == settings.llm_model
    assert client.calls == 0
