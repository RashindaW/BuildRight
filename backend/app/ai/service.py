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
from app.ai.guardrails import (
    SAFE_FALLBACK,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_TOOLS,
    validate_response,
)
from app.ai.prompts import build_user_message
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


# ---- Multi-turn chat with tool-use -------------------------------------

_MAX_TOOL_ROUNDS = 4


def _emit_chunks(text: str, size: int = 48):
    """Split a final answer into word-aligned chunks for a streaming feel."""
    words = text.split(" ")
    buf = ""
    for w in words:
        buf = w if not buf else f"{buf} {w}"
        if len(buf) >= size:
            yield buf + " "
            buf = ""
    if buf:
        yield buf


async def stream_chat(
    prior_messages: list[dict],
    menu: list[dict],
    user_question: str,
    max_tokens: int | None = None,
) -> AsyncIterator[dict]:
    """Yield SSE event dicts: {event, data}.

    The model grounds itself by calling the `search_menu` tool; we accumulate the
    items it fetched into the turn's grounded set and validate every price in the
    final answer against that set before emitting a single token. A fabricated
    price is therefore never shown.

    Events: start | delta | validated | done | error
    """
    from app.ai import tools  # local import avoids a cycle at module load

    client = _get_async_client()
    messages = list(prior_messages)
    messages.append({"role": "user", "content": user_question})

    yield {"event": "start", "data": {}}

    grounded: list[dict] = []
    final_text = ""
    input_tokens = output_tokens = 0

    try:
        for _ in range(_MAX_TOOL_ROUNDS):
            resp = await client.messages.create(
                model=models.MODEL,
                max_tokens=max_tokens or models.MAX_TOKENS,
                temperature=models.TEMPERATURE,
                system=SYSTEM_PROMPT_TOOLS,
                tools=tools.TOOLS,
                messages=messages,
            )
            input_tokens += resp.usage.input_tokens
            output_tokens += resp.usage.output_tokens

            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use" and block.name == "search_menu":
                        result_json, items = tools.execute_search_menu(block.input, menu)
                        grounded.extend(items)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_json,
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            final_text = "".join(b.text for b in resp.content if b.type == "text").strip()
            break
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError) as e:
        logger.warning('"llm_chat_error: %s"', type(e).__name__)
        yield {"event": "error", "data": {"message": models.API_ERROR_MESSAGE}}
        return

    # Deduplicate grounded items by id for the validator + persistence.
    seen, grounded_unique = set(), []
    for it in grounded:
        if it["id"] not in seen:
            seen.add(it["id"])
            grounded_unique.append(it)

    result = validate_response(final_text, grounded_unique)
    if not result.ok:
        logger.warning('"guardrail_violation_chat: %s"', result.reason)
        final_text = SAFE_FALLBACK

    # Validated in full before emitting — safe to stream chunk by chunk.
    for chunk in _emit_chunks(final_text):
        yield {"event": "delta", "data": {"text": chunk}}

    yield {
        "event": "done",
        "data": {
            "text": final_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "guardrail_violation": not result.ok,
            "grounded_item_ids": [it["id"] for it in grounded_unique],
        },
    }
