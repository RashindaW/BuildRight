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
from app.ai.context import ToolContext
from app.ai.guardrails import (
    SAFE_FALLBACK,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_RETAIL,
    validate_citations,
    validate_response,
)
from app.ai.prompts import build_memory_preamble, build_user_message
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

_MAX_TOOL_ROUNDS = 6


def _emit_chunks(text: str, size: int = 48):
    words = text.split(" ")
    buf = ""
    for w in words:
        buf = w if not buf else f"{buf} {w}"
        if len(buf) >= size:
            yield buf + " "
            buf = ""
    if buf:
        yield buf


def _build_executors():
    from app.ai import tools
    return {
        "search_menu": lambda inp, ctx: tools.execute_search_menu(inp, ctx.menu),
        "search_products": lambda inp, ctx: tools.execute_search_products(inp, ctx),
        "search_knowledge_base": lambda inp, ctx: tools.execute_search_kb(inp, ctx),
        "get_order_history": lambda inp, ctx: tools.execute_get_order_history(inp, ctx),
        "reorder": lambda inp, ctx: tools.execute_reorder(inp, ctx),
        "get_preferences": lambda inp, ctx: tools.execute_get_preferences(inp, ctx),
        "set_preference": lambda inp, ctx: tools.execute_set_preference(inp, ctx),
    }


async def stream_chat(
    prior_messages: list[dict],
    ctx: ToolContext,
    user_question: str,
    max_tokens: int | None = None,
) -> AsyncIterator[dict]:
    """Yield SSE event dicts: {event, data}.

    Grounding: the model calls search_products / search_knowledge_base;
    we accumulate grounded items (for price validation) and grounded chunks
    (for citation soft-check) before emitting any token.

    Events: start | delta | validated | done | error
    """
    from app.ai import tools  # local import avoids module-load cycle

    client = _get_async_client()
    executors = _build_executors()

    preamble = build_memory_preamble(ctx.preferences)
    effective_question = preamble + user_question if preamble else user_question

    messages = list(prior_messages)
    messages.append({"role": "user", "content": effective_question})

    yield {"event": "start", "data": {}}

    grounded_items: list[dict] = []
    grounded_chunks: list = []
    cart_dirty = False
    final_text = ""
    input_tokens = output_tokens = 0

    try:
        for _ in range(_MAX_TOOL_ROUNDS):
            resp = await client.messages.create(
                model=models.MODEL,
                max_tokens=max_tokens or models.MAX_TOKENS,
                temperature=models.TEMPERATURE,
                system=SYSTEM_PROMPT_RETAIL,
                tools=tools.TOOLS,
                messages=messages,
            )
            input_tokens += resp.usage.input_tokens
            output_tokens += resp.usage.output_tokens

            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})
                tool_results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    executor = executors.get(block.name)
                    if executor is None:
                        continue
                    result_json, payload = executor(block.input, ctx)
                    if block.name in ("search_menu", "search_products"):
                        grounded_items.extend(payload)
                    elif block.name == "search_knowledge_base":
                        grounded_chunks.extend(payload)
                    elif block.name == "reorder" and isinstance(payload, dict) and payload.get("added"):
                        cart_dirty = True
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

    # Deduplicate grounded items by id for the price validator
    seen_ids, grounded_unique = set(), []
    for it in grounded_items:
        key = it.get("slug") or it.get("id")
        if key and key not in seen_ids:
            seen_ids.add(key)
            grounded_unique.append(it)

    # Hard price guard
    result = validate_response(final_text, grounded_unique)
    if not result.ok:
        logger.warning('"guardrail_price_violation: %s"', result.reason)
        final_text = SAFE_FALLBACK

    # Soft citation check — append a disclaimer rather than replacing the answer
    citation_ok = validate_citations(final_text, grounded_chunks)
    if not citation_ok:
        logger.info('"guardrail_citation_soft: policy answer without grounded chunks"')
        final_text += (
            "\n\n_(For the most accurate policy details, please contact our customer "
            "service team or visit buildright.ca.)_"
        )

    for chunk in _emit_chunks(final_text):
        yield {"event": "delta", "data": {"text": chunk}}

    yield {
        "event": "done",
        "data": {
            "text": final_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "guardrail_violation": not result.ok,
            "grounded_item_ids": [it.get("slug") or it.get("id") for it in grounded_unique],
            "grounded_doc_ids": [c.chunk_id for c in grounded_chunks],
            "cart_dirty": cart_dirty,
        },
    }
