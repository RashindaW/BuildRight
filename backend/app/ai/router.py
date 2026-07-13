"""Multi-agent model router.

A cheap classifier (Haiku) inspects each turn and decides which model runs the
main tool loop. Simple lookups / FAQ / reorder / order-status stay on the cheap
model; multi-step "project planning", multimodal turns, and otherwise-complex
turns escalate to the heavy model (Sonnet). Guardrails are identical regardless
of which model answers.

The router is deliberately cheap and best-effort: a heuristic fast-path resolves
the obvious cases with no extra round-trip, and any classifier failure falls back
to the cheap model (fail-safe, never fail-expensive).
"""

from __future__ import annotations

import logging

import anthropic

from app.core.config import settings

logger = logging.getLogger("app.ai.router")

# Route labels
SIMPLE = "simple"
COMPLEX = "complex"
MULTIMODAL = "multimodal"

_ROUTER_SYSTEM = (
    "You are a fast request classifier for a hardware-store shopping assistant. "
    "Classify the shopper's latest message into exactly one label:\n"
    "- SIMPLE: a single product lookup, a price/stock/spec question, a policy or "
    "FAQ question, a reorder, or an order-status/history question.\n"
    "- COMPLEX: a multi-step task — planning a project (e.g. 'repair my room', "
    "'build a deck'), computing materials or quantities from measurements, "
    "comparing many options at once, or anything needing several reasoning steps.\n"
    "Reply with exactly one word: SIMPLE or COMPLEX."
)

# Heuristic fast-path: phrases that reliably mean a multi-step project. Hitting
# one of these skips the classifier round-trip entirely.
_COMPLEX_HINTS = (
    "repair",
    "renovat",
    "remodel",
    "build a",
    "build me",
    "project",
    "how much paint",
    "how many",
    "how much do i need",
    "measurement",
    "square feet",
    "sq ft",
    "square foot",
    "deck",
    "fence",
    "tile my",
    "paint my",
    "redo my",
    "install a",
    "renovate",
)


async def classify_turn(
    client: anthropic.AsyncAnthropic,
    user_question: str,
    *,
    has_image: bool = False,
    model: str | None = None,
) -> tuple[str, str]:
    """Classify a turn and pick the model that should run the tool loop.

    Returns ``(label, model_id)``. Best-effort: defaults to the cheap model on
    anything ambiguous or on any classifier error.

    When router v2 is enabled, dispatches to the learned zero-latency policy
    (registry candidates + difficulty head + cost-quality trade-off); this v1
    heuristic+LLM path remains the flag-off fallback and the safety net.
    """
    if not settings.model_router_enabled:
        return SIMPLE, settings.llm_model

    if settings.router_v2_enabled:
        try:
            from app.ai.routing.policy import decide
            d = decide(user_question, has_image=has_image)
            if d is not None:
                logger.info('"route_v2: %s difficulty=%.2f candidates=%d"',
                            d.model_id, d.predicted_difficulty, d.candidates)
                return d.label, d.model_id
        except Exception:  # noqa: BLE001 - v2 must never take chat down
            logger.exception("router v2 failed — falling back to v1")

    # An image always escalates — vision turns need the heavy model.
    if has_image:
        return MULTIMODAL, settings.llm_model_heavy

    q = (user_question or "").lower()

    # Obvious project language → escalate without spending a classify call.
    if any(hint in q for hint in _COMPLEX_HINTS):
        return COMPLEX, settings.llm_model_heavy

    # Very short messages are almost always simple lookups; don't pay for a call.
    if len(q.strip()) < 12:
        return SIMPLE, settings.llm_model

    try:
        resp = await client.messages.create(
            model=model or settings.llm_router_model,
            max_tokens=4,
            temperature=0.0,
            system=_ROUTER_SYSTEM,
            messages=[{"role": "user", "content": user_question[:600]}],
        )
        label_text = "".join(
            b.text for b in resp.content if b.type == "text"
        ).strip().upper()
    except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APIError) as e:
        logger.info('"router_classify_failed: %s"', type(e).__name__)
        return SIMPLE, settings.llm_model

    if label_text.startswith("COMPLEX"):
        return COMPLEX, settings.llm_model_heavy
    return SIMPLE, settings.llm_model
