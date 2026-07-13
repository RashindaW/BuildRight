"""Model registry — the config-driven catalog of every model the app can route to.

Loaded from models.yaml (path overridable via MODELS_CONFIG). Each entry declares its
provider type, credentials env, pricing, and capabilities; adding a model is a YAML
edit, not code surgery. The registry exposes:

  get(model_id)            → ModelEntry | None
  acquire(model_id, fallback_client=None) → LLMProvider for the entry
  routable(capability=None) → configured + healthy entries (credentials resolve)
  mark_unhealthy/mark_healthy(model_id)   → health bookkeeping (used by the pool loop)
  provider_status()        → {provider_name: bool} for /health/ready

Anthropic-routed models are served through ClientAdapter over the client factory in
service.py — which is also the seam test fakes monkeypatch, so the whole test-suite
exercises the provider layer with zero fixture churn.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("app.ai.registry")

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "models.yaml"


@dataclass
class ModelEntry:
    id: str
    provider: str                      # "anthropic" | "openai_compat"
    model: str                         # provider-native name
    api_key_env: str = ""
    base_url: str | None = None
    price_in: float = 0.0              # $/Mtok
    price_out: float = 0.0
    capabilities: list[str] = field(default_factory=list)
    context_window: int = 0
    latency_class: str = "fast"
    roles: list[str] = field(default_factory=list)
    enabled: bool = True
    healthy: bool = True               # flipped by health checks; True by default

    @property
    def api_key(self) -> str:
        if self.provider == "anthropic":
            # honor the pydantic-managed secret (tests set it via env/monkeypatch)
            return settings.anthropic_api_key.get_secret_value()
        return os.environ.get(self.api_key_env, "") if self.api_key_env else ""

    @property
    def configured(self) -> bool:
        """Credentials resolve (and base_url present for openai_compat)."""
        if not self.enabled:
            return False
        if self.provider == "openai_compat" and not self.base_url:
            return False
        return bool(self.api_key)


class _Registry:
    def __init__(self):
        self._entries: dict[str, ModelEntry] | None = None
        self._providers: dict[str, object] = {}

    # -- loading -------------------------------------------------------------

    def _load(self) -> dict[str, ModelEntry]:
        if self._entries is not None:
            return self._entries
        path = Path(os.environ.get("MODELS_CONFIG", str(_DEFAULT_PATH)))
        entries: dict[str, ModelEntry] = {}
        try:
            import yaml
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for m in raw.get("models", []):
                e = ModelEntry(**{k: v for k, v in m.items() if k in ModelEntry.__dataclass_fields__})
                entries[e.id] = e
        except FileNotFoundError:
            logger.warning("models.yaml not found at %s — using built-in Claude defaults", path)
        except Exception:  # noqa: BLE001 - a malformed registry must not kill the app
            logger.exception("models.yaml failed to load — using built-in Claude defaults")
        if not entries:
            for mid, latency, roles, (pi, po) in (
                (settings.llm_model, "fast", ["fast", "router"], (1.0, 5.0)),
                (settings.llm_model_heavy, "heavy", ["heavy", "vision"], (3.0, 15.0)),
            ):
                entries[mid] = ModelEntry(
                    id=mid, provider="anthropic", model=mid, api_key_env="ANTHROPIC_API_KEY",
                    price_in=pi, price_out=po, capabilities=["tools", "vision", "streaming"],
                    context_window=200_000, latency_class=latency, roles=roles,
                )
        self._entries = entries
        return entries

    def reload(self) -> None:
        """Drop caches (tests / config changes)."""
        self._entries = None
        self._providers = {}

    # -- lookups ---------------------------------------------------------------

    def get(self, model_id: str) -> ModelEntry | None:
        return self._load().get(model_id)

    def all(self) -> list[ModelEntry]:
        return list(self._load().values())

    def routable(self, capability: str | None = None) -> list[ModelEntry]:
        out = [e for e in self._load().values() if e.configured and e.healthy]
        if capability:
            out = [e for e in out if capability in e.capabilities]
        return out

    def mark_unhealthy(self, model_id: str) -> None:
        e = self.get(model_id)
        if e and e.healthy:
            e.healthy = False
            logger.warning('"model_marked_unhealthy: %s"', model_id)

    def mark_healthy(self, model_id: str) -> None:
        e = self.get(model_id)
        if e and not e.healthy:
            e.healthy = True
            logger.info('"model_marked_healthy: %s"', model_id)

    def provider_status(self) -> dict[str, bool]:
        """{provider_label: any-configured} for the readiness probe."""
        status: dict[str, bool] = {}
        for e in self._load().values():
            if not e.enabled:
                continue
            label = e.provider if e.provider != "openai_compat" else e.id
            status[label] = status.get(label, False) or e.configured
        return status

    # -- providers ---------------------------------------------------------------

    def acquire(self, model_id: str, fallback_client=None):
        """An LLMProvider for `model_id`.

        anthropic entries (and unknown ids, for back-compat) wrap `fallback_client`
        when given — the seam the test fakes flow through — else the real SDK client.
        openai_compat entries get a cached OpenAICompatProvider.
        """
        from app.ai.providers.base import ClientAdapter

        entry = self.get(model_id)
        if entry is None or entry.provider == "anthropic":
            if fallback_client is not None:
                return ClientAdapter(fallback_client, streaming_enabled=settings.stream_tokens_enabled)
            from app.ai import service
            return ClientAdapter(service._get_async_client(),
                                 streaming_enabled=settings.stream_tokens_enabled)

        if entry.provider == "openai_compat":
            prov = self._providers.get(entry.id)
            if prov is None:
                from app.ai.providers.openai_compat import OpenAICompatProvider
                prov = OpenAICompatProvider(
                    name=entry.id, model=entry.model, base_url=entry.base_url,
                    api_key=entry.api_key,
                    streaming="streaming" in entry.capabilities and settings.stream_tokens_enabled,
                )
                self._providers[entry.id] = prov
            return prov

        raise ValueError(f"unknown provider type '{entry.provider}' for model '{model_id}'")


registry = _Registry()
