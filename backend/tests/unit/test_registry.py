"""Model registry: loading, credential gating, health marks, provider acquisition."""

from __future__ import annotations

import pytest

from app.ai.providers.base import ClientAdapter
from app.ai.registry import registry


@pytest.fixture(autouse=True)
def _fresh_registry():
    registry.reload()
    yield
    registry.reload()


def test_registry_loads_models_yaml():
    entries = {e.id for e in registry.all()}
    assert "claude-haiku-4-5" in entries and "claude-sonnet-4-6" in entries
    assert "groq-llama-70b" in entries  # free-tier cloud entry ships in the file


def test_anthropic_entries_configured_with_key():
    e = registry.get("claude-haiku-4-5")
    assert e is not None and e.configured  # conftest sets ANTHROPIC_API_KEY


def test_openai_compat_gated_on_env_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    e = registry.get("groq-llama-70b")
    assert e is not None and not e.configured
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    assert e.configured


def test_routable_respects_capability_and_health(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    ids = {e.id for e in registry.routable("vision")}
    assert "claude-sonnet-4-6" in ids
    assert "groq-llama-70b" not in ids  # no vision capability
    registry.mark_unhealthy("groq-llama-70b")
    assert "groq-llama-70b" not in {e.id for e in registry.routable()}
    registry.mark_healthy("groq-llama-70b")
    assert "groq-llama-70b" in {e.id for e in registry.routable()}


def test_acquire_wraps_fallback_client_for_anthropic_and_unknown():
    fake = object.__new__(object)  # any object; adapter only touches .messages at call time

    class _Fake:
        messages = None

    prov = registry.acquire("claude-haiku-4-5", fallback_client=_Fake())
    assert isinstance(prov, ClientAdapter)
    prov2 = registry.acquire("model-not-in-registry", fallback_client=_Fake())
    assert isinstance(prov2, ClientAdapter)  # back-compat: unknown ids wrap the client


def test_acquire_openai_compat_is_cached(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    p1 = registry.acquire("groq-llama-70b")
    p2 = registry.acquire("groq-llama-70b")
    assert p1 is p2
    assert p1.name == "groq-llama-70b"


def test_provider_status_reports_configured():
    status = registry.provider_status()
    assert status.get("anthropic") is True  # key set by conftest
