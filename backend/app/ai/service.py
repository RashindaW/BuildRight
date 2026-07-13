"""Assistant service: the LLM call + guardrail enforcement.

- complete(): single-turn, used by the legacy golden-test wrapper.
- stream_chat(): multi-turn async generator emitting SSE events with TRUE token
  streaming guarded by StreamingPriceGate — each price is validated the moment it
  completes, so a fabricated price never renders, even transiently mid-stream.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator

import anthropic

from app.ai import models
from app.ai.context import ToolContext
from app.ai.guardrails import (
    SAFE_FALLBACK,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_RETAIL,
    StreamingPriceGate,
    extract_prices,
    validate_citations,
    validate_response,
)
from app.ai.pricing import cost_usd
from app.ai.prompts import build_memory_preamble, build_user_message
from app.ai.providers.base import ProviderError
from app.ai.registry import registry
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


def summarize_need(messages: list[dict]) -> str:
    """Best-effort 1-line summary of what the customer is looking for (session memory).

    Cheap (Haiku, tiny output) and OFF the user-visible path — call it after the SSE
    stream has already finished. Returns "" on any failure; never raises.
    """
    transcript = []
    for m in messages[-8:]:
        content = m.get("content")
        if isinstance(content, str) and content.strip():
            transcript.append(f"{m.get('role', '?')}: {content[:300]}")
    if not transcript:
        return ""
    try:
        resp = _get_sync_client().messages.create(
            model=models.MODEL,
            max_tokens=40,
            temperature=0.0,
            system=("Summarize, in ONE short line (max 18 words), what this hardware-store "
                    "customer is looking for or working on. No preamble, just the line."),
            messages=[{"role": "user", "content": "\n".join(transcript)}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()[:400]
    except Exception:  # noqa: BLE001 - summary is optional; never break persistence
        logger.info('"conversation_summary_failed"')
        return ""


# ---- Multi-turn chat with tool-use -------------------------------------

_MAX_TOOL_ROUNDS = 6


# Round streaming lives in the provider layer now (providers/base.py ClientAdapter +
# providers/openai_compat.py): each provider yields ("delta", text)* then ("final",
# LLMResponse), and the registry picks the adapter for the routed model.


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
        "compute_materials": lambda inp, ctx: tools.execute_compute_materials(inp, ctx),
        "add_materials_to_cart": lambda inp, ctx: tools.execute_add_materials_to_cart(inp, ctx),
        "suggest_complementary": lambda inp, ctx: tools.execute_suggest_complementary(inp, ctx),
        "recommend_similar": lambda inp, ctx: tools.execute_recommend_similar(inp, ctx),
        "frequently_bought_with": lambda inp, ctx: tools.execute_frequently_bought_with(inp, ctx),
    }


# Friendly "what the agent is doing right now" labels, keyed by tool name. Surfaced as
# SSE `status` events so the chat can show live progress instead of a static spinner.
_TOOL_STATUS = {
    "search_products": "Searching the catalog…",
    "search_menu": "Searching the catalog…",
    "search_knowledge_base": "Checking our policies & guides…",
    "recommend_similar": "Finding good matches…",
    "frequently_bought_with": "Finding what pairs well…",
    "suggest_complementary": "Finding what pairs well…",
    "graph_recommend": "Finding good matches…",
    "compute_materials": "Planning your project…",
    "add_materials_to_cart": "Adding items to your cart…",
    "reorder": "Pulling up your past orders…",
    "get_order_history": "Looking up your orders…",
    "get_inventory": "Checking inventory…",
    "get_margins": "Crunching the margins…",
    "get_ai_attribution": "Attributing AI-driven sales…",
    "get_ai_ops": "Reviewing AI operations…",
    "get_csat": "Reading satisfaction scores…",
    "get_chat_quality": "Scoring chat quality…",
}


def _tool_status(names: list[str]) -> dict:
    """Pick a friendly label for a round of tool calls (first recognized tool wins)."""
    for n in names:
        if n in _TOOL_STATUS:
            return {"phase": "working", "label": _TOOL_STATUS[n]}
    return {"phase": "working", "label": "Working on it…"}


async def stream_chat(
    prior_messages: list[dict],
    ctx: ToolContext,
    user_question: str,
    max_tokens: int | None = None,
    has_image: bool = False,
    *,
    system_prompt: str | None = None,
    tools_override: list | None = None,
    executors_override: dict | None = None,
    validate_prices: bool = True,
    _forced_model: str | None = None,
    _attempt: int = 1,
) -> AsyncIterator[dict]:
    """Yield SSE event dicts: {event, data}.

    Grounding: the model calls search_products / search_knowledge_base;
    we accumulate grounded items (for price validation) and grounded chunks
    (for citation soft-check) before emitting any token.

    A cheap router classifies the turn first (see ai/router.py): simple turns
    run on the cheap model, while project-planning / multimodal / complex turns
    escalate to the heavy model. Guardrails apply identically either way.

    Events: start | status | delta | delta_reset | validated | done | error
    """
    from app.ai import router  # local import avoids module-load cycle
    from app.ai import tools

    client = _get_async_client()
    executors = executors_override if executors_override is not None else _build_executors()
    sys_prompt = system_prompt or SYSTEM_PROMPT_RETAIL
    tool_defs = tools_override if tools_override is not None else tools.TOOLS

    # Semantic cache: first-turn GUEST questions (no history, no memory) may be served
    # instantly from a validated cached answer — $0, ~0ms, stale prices re-checked.
    cacheable = (
        validate_prices and _attempt == 1 and not prior_messages
        and not ctx.user_id and ctx.db is not None
    )
    if cacheable:
        from app.ai import semantic_cache
        hit = semantic_cache.lookup(ctx.db, user_question)
        if hit is not None:
            yield {"event": "start", "data": {"model": "semantic-cache", "route": "cache"}}
            yield {"event": "trace", "data": {"type": "cache", "hit": True}}
            yield {"event": "delta", "data": {"text": hit.text}}
            yield {"event": "trace", "data": {"type": "guardrail", "ok": True,
                                              "prices_checked": len(extract_prices(hit.text))}}
            yield {"event": "trace", "data": {"type": "cost", "usd": 0.0, "saved_pct": 100}}
            yield {"event": "done", "data": {
                "text": hit.text, "input_tokens": 0, "output_tokens": 0,
                "guardrail_violation": False,
                "grounded_item_ids": hit.grounded_item_ids, "grounded_doc_ids": [],
                "cart_dirty": False, "model": "semantic-cache", "route": "cache",
                "tools_used": [], "tool_rounds": 0,
                "predicted_difficulty": None, "escalated": False,
                "router_version": "cache", "cost_usd": 0.0, "cache": "semantic",
            }}
            return

    # Route once per turn; the chosen model drives every round of the tool loop.
    if _forced_model:
        route_label, route_model = "escalated", _forced_model  # cascade second opinion
    else:
        route_label, route_model = await router.classify_turn(
            client, user_question, has_image=has_image
        )
    # Resolve the routed model to its provider (anthropic entries — and test fakes —
    # wrap `client`; openai_compat entries get their own adapter from the registry).
    provider = registry.acquire(route_model, fallback_client=client)

    # Learned-difficulty telemetry (zero-latency NumPy head; None when v2 is off).
    predicted_difficulty: float | None = None
    if settings.router_v2_enabled:
        try:
            from app.ai.routing.difficulty import p_cheap_ok
            predicted_difficulty = round(1.0 - p_cheap_ok(user_question, has_image=has_image), 3)
        except Exception:  # noqa: BLE001
            predicted_difficulty = None

    preamble = build_memory_preamble(ctx.preferences)
    effective_question = preamble + user_question if preamble else user_question

    messages = list(prior_messages)
    messages.append({"role": "user", "content": effective_question})

    yield {"event": "start", "data": {"model": route_model, "route": route_label}}
    yield {"event": "status", "data": {"phase": "thinking", "label": "Thinking…"}}
    # Glass-box trace: surface the routing decision (which brain, and why) to the UI.
    yield {"event": "trace", "data": {
        "type": "route", "model": route_model, "label": route_label,
        "predicted_difficulty": predicted_difficulty,
    }}

    grounded_items: list[dict] = []
    grounded_chunks: list = []
    cart_dirty = False
    final_text = ""
    completed = False
    guardrail_violation = False
    input_tokens = output_tokens = 0
    tools_used: list[str] = []   # tool-use trace for observability
    tool_rounds = 0

    # Prices the assistant already stated (and that passed validation) earlier in this
    # conversation are still trusted now — carry them forward so multi-turn references
    # and computed line totals don't trip the guardrail. Needed BEFORE generation now
    # that prices are validated token-by-token as they stream.
    carried_prices: set[str] = set()
    for m in prior_messages:
        if isinstance(m, dict) and m.get("role") == "assistant" and isinstance(m.get("content"), str):
            carried_prices |= extract_prices(m["content"])

    try:
        for _ in range(_MAX_TOOL_ROUNDS):
            # Token-true guardrail: grounded prices are fully known before this round's
            # text is generated (tool rounds precede the answer), so each price is
            # validated the moment it completes — an unvalidated price never renders.
            gate = (
                StreamingPriceGate(grounded_items, extra_allowed=carried_prices, allow_multiples=True)
                if validate_prices
                else None
            )
            round_text = ""

            agen = provider.stream_events(
                model=route_model,
                max_tokens=max_tokens or models.MAX_TOKENS,
                temperature=models.TEMPERATURE,
                system=sys_prompt,
                tools=tool_defs,
                messages=messages,
            )
            resp = None
            async for kind, val in agen:
                if kind == "delta":
                    out = gate.feed(val) if gate else val
                    if gate and gate.violation:
                        # Abort the stream; the post-loop block escalates or replaces.
                        await agen.aclose()
                        logger.warning('"guardrail_price_violation_stream: %s"', gate.violation)
                        final_text = SAFE_FALLBACK
                        guardrail_violation = True
                        completed = True
                        break
                    if out:
                        round_text += out
                        yield {"event": "delta", "data": {"text": out}}
                else:  # ("final", resp)
                    resp = val
            if guardrail_violation:
                break
            if resp is None:  # stream ended without a final message (defensive)
                break
            input_tokens += resp.usage.input_tokens
            output_tokens += resp.usage.output_tokens

            if resp.stop_reason == "tool_use":
                # Any preamble text shown this round is interim — tell the client to
                # clear it before the next round streams (it is not persisted).
                if round_text:
                    yield {"event": "delta_reset", "data": {}}
                tool_rounds += 1
                messages.append({"role": "assistant", "content": resp.content})
                round_tools = [b.name for b in resp.content if b.type == "tool_use"]
                yield {"event": "status", "data": _tool_status(round_tools)}
                tool_results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    tools_used.append(block.name)
                    executor = executors.get(block.name)
                    if executor is None:
                        continue
                    # A malformed tool_input must not abort the whole stream — return
                    # an error tool_result instead so the model can recover.
                    _t0 = time.perf_counter()
                    try:
                        result_json, payload = executor(block.input, ctx)
                    except Exception as e:
                        logger.warning('"tool_exec_error: %s %s"', block.name, type(e).__name__)
                        result_json, payload = json.dumps({"error": "tool_failed"}), None
                    yield {"event": "trace", "data": {
                        "type": "tool", "name": block.name,
                        "ms": round((time.perf_counter() - _t0) * 1000),
                    }}
                    if payload is not None and block.name in (
                        "search_menu", "search_products", "get_order_history",
                        "compute_materials", "suggest_complementary",
                        "recommend_similar", "frequently_bought_with",
                    ):
                        grounded_items.extend(payload)
                    elif payload is not None and block.name == "search_knowledge_base":
                        grounded_chunks.extend(payload)
                    elif block.name in ("reorder", "add_materials_to_cart") and isinstance(payload, dict):
                        if payload.get("added"):
                            cart_dirty = True
                        # Ground the added items' unit + line-total prices.
                        grounded_items.extend(payload.get("grounded", []))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_json,
                    })
                messages.append({"role": "user", "content": tool_results})
                yield {"event": "status", "data": {"phase": "summarizing", "label": "Summarizing what I found…"}}
                continue

            # Final (non-tool) round: release the gate's held tail — it may still
            # catch a violation in the last few characters.
            tail = gate.finish() if gate else ""
            if gate and gate.violation:
                logger.warning('"guardrail_price_violation_stream: %s"', gate.violation)
                final_text = SAFE_FALLBACK
                guardrail_violation = True
            else:
                if tail:
                    round_text += tail
                    yield {"event": "delta", "data": {"text": tail}}
                final_text = round_text.strip()
            completed = True
            break

    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError,
            ProviderError) as e:
        logger.warning('"llm_chat_error: %s"', type(e).__name__)
        if isinstance(e, ProviderError) and e.retryable:
            registry.mark_unhealthy(route_model)  # next turns route around it
            # Provider failover: retry this turn once on the strongest healthy model —
            # a dead GPU pool degrades to the API tier instead of erroring at the user.
            if _attempt == 1:
                try:
                    from app.ai.routing.policy import strongest_healthy
                    alt = strongest_healthy(exclude=route_model)
                except Exception:  # noqa: BLE001
                    alt = None
                if alt and alt != route_model:
                    logger.info('"provider_failover: %s -> %s"', route_model, alt)
                    yield {"event": "status", "data": {"phase": "failover", "label": "Switching to a backup model…"}}
                    yield {"event": "delta_reset", "data": {}}
                    yield {"event": "trace", "data": {"type": "escalation", "from": route_model, "to": alt}}
                    async for ev in stream_chat(
                        prior_messages, ctx, user_question, max_tokens, has_image,
                        system_prompt=system_prompt, tools_override=tools_override,
                        executors_override=executors_override, validate_prices=validate_prices,
                        _forced_model=alt, _attempt=2,
                    ):
                        if ev["event"] != "start":
                            yield ev
                    return
        yield {"event": "error", "data": {"message": models.API_ERROR_MESSAGE}}
        return

    # Guardrail violation: CASCADE — a failed cheap answer earns one visible retry on
    # the strongest healthy model before we settle for the safe fallback.
    if guardrail_violation:
        escalate_to: str | None = None
        if settings.router_cascade_enabled and validate_prices and _attempt == 1:
            try:
                from app.ai.routing.policy import strongest_healthy
                cand = strongest_healthy(exclude=route_model)
                if cand and cand != route_model:
                    escalate_to = cand
            except Exception:  # noqa: BLE001
                escalate_to = None
        if escalate_to:
            logger.info('"cascade_escalation: %s -> %s"', route_model, escalate_to)
            yield {"event": "status", "data": {"phase": "escalating", "label": "Getting a second opinion…"}}
            yield {"event": "delta_reset", "data": {}}
            yield {"event": "trace", "data": {"type": "escalation", "from": route_model, "to": escalate_to}}
            async for ev in stream_chat(
                prior_messages, ctx, user_question, max_tokens, has_image,
                system_prompt=system_prompt, tools_override=tools_override,
                executors_override=executors_override, validate_prices=validate_prices,
                _forced_model=escalate_to, _attempt=2,
            ):
                if ev["event"] != "start":  # a single logical turn: keep the outer start
                    yield ev
            return
        yield {"event": "validated", "data": {"replace": True, "text": SAFE_FALLBACK}}

    # If the model never stopped calling tools (rounds exhausted) or produced no text,
    # substitute a fallback rather than emitting/persisting a silent blank turn. The
    # fallback must also be DELIVERED (nothing, or only since-reset interim text, has
    # been shown for it).
    if not completed or not final_text:
        logger.warning('"llm_chat_tool_rounds_exhausted_or_empty: completed=%s"', completed)
        final_text = SAFE_FALLBACK
        yield {"event": "validated", "data": {"replace": True, "text": SAFE_FALLBACK}}

    # Deduplicate grounded items by id (for the done event / downstream consumers)
    seen_ids, grounded_unique = set(), []
    for it in grounded_items:
        key = it.get("slug") or it.get("id")
        if key and key not in seen_ids:
            seen_ids.add(key)
            grounded_unique.append(it)

    # Soft citation check — append a disclaimer rather than replacing the answer.
    # The answer already streamed, so the disclaimer is delivered as one more delta.
    if not guardrail_violation:
        citation_ok = validate_citations(final_text, grounded_chunks)
        if not citation_ok:
            logger.info('"guardrail_citation_soft: policy answer without grounded chunks"')
            disclaimer = (
                "\n\n_(For the most accurate policy details, please contact our customer "
                "service team or visit buildright.ca.)_"
            )
            final_text += disclaimer
            yield {"event": "delta", "data": {"text": disclaimer}}

    if validate_prices:
        yield {"event": "trace", "data": {
            "type": "guardrail",
            "ok": not guardrail_violation,
            "prices_checked": len(extract_prices(final_text)),
        }}

    # A clean, grounded first-turn guest answer becomes a cache entry for the next visitor.
    if cacheable and completed and not guardrail_violation and final_text != SAFE_FALLBACK:
        from app.ai import semantic_cache
        semantic_cache.store(
            ctx.db, user_question, final_text,
            [it.get("slug") or it.get("id") for it in grounded_unique],
        )

    # Cost transparency: what this turn cost vs the always-heavy counterfactual.
    turn_cost = cost_usd(route_model, input_tokens, output_tokens)
    heavy_cost = cost_usd(settings.llm_model_heavy, input_tokens, output_tokens)
    saved_pct = round((1 - turn_cost / heavy_cost) * 100) if heavy_cost > 0 and turn_cost < heavy_cost else 0
    yield {"event": "trace", "data": {"type": "cost", "usd": round(turn_cost, 5), "saved_pct": saved_pct}}

    yield {
        "event": "done",
        "data": {
            "text": final_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "guardrail_violation": guardrail_violation,
            "grounded_item_ids": [it.get("slug") or it.get("id") for it in grounded_unique],
            "grounded_doc_ids": [c.chunk_id for c in grounded_chunks],
            "cart_dirty": cart_dirty,
            "model": route_model,
            "route": route_label,
            "tools_used": tools_used,
            "tool_rounds": tool_rounds,
            "predicted_difficulty": predicted_difficulty,
            "escalated": _attempt > 1,
            "router_version": "v2" if settings.router_v2_enabled else "v1",
            "cost_usd": cost_usd(route_model, input_tokens, output_tokens),
        },
    }
