"""Assistant service: the LLM call + guardrail enforcement.

- complete(): single-turn, used by the legacy golden-test wrapper.
- stream_chat(): multi-turn async generator emitting SSE events with
  buffer-on-price validation (a fabricated price never renders, even mid-stream).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import anthropic

from app.ai import models
from app.ai.guardrails import SAFE_FALLBACK, SYSTEM_PROMPT, validate_response
from app.ai.prompts import build_grounded_turn, build_user_message
from app.core.config import settings

logger = logging.getLogger("app.ai")

_sync_client: anthropic.Anthropic | None = None
_async_client: anthropic.AsyncAnthropic | None = None


def _api_key() -> str:
    return settings.anthropic_api_key.get_secret_value()


def _get_sync_client() -> anthropic.Anthropic:
    global _sync_client
    if _sync_client is None:
        _sync_client = anthropic.Anthropic(api_key=_api_key())
    return _sync_client


def _get_async_client() -> anthropic.AsyncAnthropic:
    global _async_client
    if _async_client is None:
        _async_client = anthropic.AsyncAnthropic(api_key=_api_key())
    return _async_client


# ---- Single-turn (golden-test surface) ---------------------------------

def complete(user_question: str, grounded_items: list[dict], max_tokens: int | None = None) -> str:
    user_message = build_user_message(grounded_items, user_question)
    try:
        response = _get_sync_client().messages.create(
            model=models.MODEL,
            max_tokens=max_tokens or models.MAX_TOKENS,
            temperature=models.TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError):
        return models.API_ERROR_MESSAGE

    text = response.content[0].text.strip()
    result = validate_response(text, grounded_items)
    if not result.ok:
        logger.warning('"guardrail_violation: %s"', result.reason)
        return SAFE_FALLBACK
    return text


# ---- Multi-turn streaming ----------------------------------------------

async def stream_chat(
    prior_messages: list[dict],
    grounded_items: list[dict],
    user_question: str,
    max_tokens: int | None = None,
) -> AsyncIterator[dict]:
    """Yield SSE event dicts: {event, data}.

    Events: start | delta | validated | done | error
    Buffer-on-price: any chunk containing a '$' is held until the full text is
    validated, so an ungrounded price is never emitted.
    """
    messages = list(prior_messages)
    messages.append({"role": "user", "content": build_grounded_turn(grounded_items, user_question)})

    yield {"event": "start", "data": {}}

    full_text = ""
    pending = ""  # buffered text that contains an unvalidated price
    input_tokens = 0
    output_tokens = 0

    try:
        async with _get_async_client().messages.stream(
            model=models.MODEL,
            max_tokens=max_tokens or models.MAX_TOKENS,
            temperature=models.TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_text += text
                pending += text
                # If the buffer holds a '$', keep buffering until validated.
                if "$" in pending:
                    continue
                yield {"event": "delta", "data": {"text": pending}}
                pending = ""

            final = await stream.get_final_message()
            input_tokens = final.usage.input_tokens
            output_tokens = final.usage.output_tokens

    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError) as e:
        logger.warning('"llm_stream_error: %s"', type(e).__name__)
        yield {"event": "error", "data": {"message": models.API_ERROR_MESSAGE}}
        return

    # Validate the complete answer against the grounded set.
    result = validate_response(full_text, grounded_items)
    if not result.ok:
        logger.warning('"guardrail_violation_stream: %s"', result.reason)
        # Replace the entire answer — never show the fabricated price.
        yield {"event": "validated", "data": {"replace": True, "text": SAFE_FALLBACK}}
        yield {
            "event": "done",
            "data": {
                "text": SAFE_FALLBACK,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "guardrail_violation": True,
            },
        }
        return

    # Flush any buffered (price-bearing but validated) tail.
    if pending:
        yield {"event": "delta", "data": {"text": pending}}

    yield {
        "event": "done",
        "data": {
            "text": full_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "guardrail_violation": False,
        },
    }
