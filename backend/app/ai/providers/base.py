"""Provider abstraction — the seam that makes the model pool heterogeneous.

Design decisions (see docs/ARCHITECTURE.md):
- The CANONICAL internal message/tool format is Anthropic-shaped (content blocks with
  .type/.text/.name/.id/.input, tools with input_schema). Message history already
  persists this shape; adapters translate at their own boundary.
- `ClientAdapter` wraps any anthropic-shaped client — the real SDK client OR the simple
  fakes used across the test-suite (objects exposing `messages.create`), so every
  existing test flows through the provider layer unchanged.
- Exceptions are normalized to the ProviderError taxonomy; call sites catch ONE type.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol


# ---- Exception taxonomy -----------------------------------------------------

class ProviderError(Exception):
    """Base for all provider failures. `retryable` hints at fallback behavior."""

    def __init__(self, message: str = "", *, provider: str = "", model: str = "", retryable: bool = False):
        super().__init__(message or self.__class__.__name__)
        self.provider = provider
        self.model = model
        self.retryable = retryable


class ProviderConnectionError(ProviderError):
    def __init__(self, message: str = "", **kw):
        super().__init__(message, retryable=True, **{k: v for k, v in kw.items() if k != "retryable"})


class ProviderRateLimitError(ProviderError):
    def __init__(self, message: str = "", **kw):
        super().__init__(message, retryable=True, **{k: v for k, v in kw.items() if k != "retryable"})


class ProviderBadRequestError(ProviderError):
    pass


class ProviderServerError(ProviderError):
    def __init__(self, message: str = "", **kw):
        super().__init__(message, retryable=True, **{k: v for k, v in kw.items() if k != "retryable"})


# ---- Normalized response shapes ---------------------------------------------

@dataclass
class Block:
    """A content block mimicking the Anthropic SDK attribute surface, so downstream
    code (`b.type == "tool_use"`, `b.text`, `b.name`, `b.id`, `b.input`) is unchanged."""

    type: str
    text: str = ""
    name: str = ""
    id: str = ""
    input: dict = field(default_factory=dict)


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    content: list[Any]          # Anthropic SDK blocks or Block dataclasses
    stop_reason: str            # "end_turn" | "tool_use" | ...
    usage: Usage
    model: str = ""


class LLMProvider(Protocol):
    """A model endpoint the agent loop can drive. `stream_events` yields
    ("delta", text) events followed by exactly one ("final", LLMResponse)."""

    name: str

    async def complete(self, **kwargs) -> LLMResponse: ...

    def stream_events(self, **kwargs) -> AsyncIterator[tuple[str, Any]]: ...


# ---- Anthropic-shaped client adapter -----------------------------------------

def _map_anthropic_error(e: Exception, model: str = "") -> ProviderError | None:
    """Translate anthropic SDK exceptions into the taxonomy (None = not anthropic's)."""
    try:
        import anthropic
    except ImportError:  # pragma: no cover
        return None
    if isinstance(e, anthropic.RateLimitError):
        return ProviderRateLimitError(str(e), provider="anthropic", model=model)
    if isinstance(e, anthropic.APIConnectionError):
        return ProviderConnectionError(str(e), provider="anthropic", model=model)
    if isinstance(e, anthropic.BadRequestError):
        return ProviderBadRequestError(str(e), provider="anthropic", model=model)
    if isinstance(e, anthropic.APIError):
        return ProviderServerError(str(e), provider="anthropic", model=model)
    return None


class ClientAdapter:
    """Wraps an anthropic-shaped client (the real SDK client or a test fake exposing
    `messages.create` / optionally `messages.stream`) behind the LLMProvider protocol."""

    name = "anthropic"

    def __init__(self, client: Any, streaming_enabled: bool = True):
        self._client = client
        self._streaming = streaming_enabled

    async def complete(self, **kwargs) -> LLMResponse:
        try:
            resp = await self._client.messages.create(**kwargs)
        except Exception as e:  # noqa: BLE001 - normalized below
            mapped = _map_anthropic_error(e, kwargs.get("model", ""))
            if mapped is not None:
                raise mapped from e
            raise
        return LLMResponse(
            content=list(resp.content),
            stop_reason=resp.stop_reason,
            usage=Usage(resp.usage.input_tokens, resp.usage.output_tokens),
            model=kwargs.get("model", ""),
        )

    async def stream_events(self, **kwargs) -> AsyncIterator[tuple[str, Any]]:
        """("delta", text)* then ("final", LLMResponse). Clients without `.stream`
        (test fakes) run buffered: one delta carrying the full text, then final."""
        stream_ctx = getattr(self._client.messages, "stream", None)
        if stream_ctx is None or not self._streaming:
            resp = await self.complete(**kwargs)
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            if text:
                yield ("delta", text)
            yield ("final", resp)
            return
        try:
            async with self._client.messages.stream(**kwargs) as s:
                async for ev in s:
                    if (
                        getattr(ev, "type", "") == "content_block_delta"
                        and getattr(getattr(ev, "delta", None), "type", "") == "text_delta"
                    ):
                        yield ("delta", ev.delta.text)
                raw = await s.get_final_message()
            yield ("final", LLMResponse(
                content=list(raw.content),
                stop_reason=raw.stop_reason,
                usage=Usage(raw.usage.input_tokens, raw.usage.output_tokens),
                model=kwargs.get("model", ""),
            ))
        except Exception as e:  # noqa: BLE001
            mapped = _map_anthropic_error(e, kwargs.get("model", ""))
            if mapped is not None:
                raise mapped from e
            raise
