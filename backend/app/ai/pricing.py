"""Token → USD cost estimation for observability.

Rates are USD per MILLION tokens (input, output), approximate published Anthropic
list prices — treat as configurable estimates, not billing truth. Matching is by
model-family prefix so version suffixes (e.g. -20251001) still resolve. An unknown
model costs 0 (logged), so cost accounting never raises.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("app.ai.pricing")

# family prefix -> (input $/Mtok, output $/Mtok)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku": (1.00, 5.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-sonnet": (3.00, 15.00),
    "claude-opus": (15.00, 75.00),
}

_PER_MILLION = 1_000_000


def _rates(model: str | None) -> tuple[float, float] | None:
    if not model:
        return None
    m = model.lower()
    # Longest-prefix match wins (so 'claude-3-5-haiku' beats 'claude-haiku').
    best = None
    for prefix, rates in MODEL_PRICING.items():
        if m.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, rates)
    return best[1] if best else None


def cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float:
    """Estimated USD cost of a turn. Unknown model → 0.0 (logged once-ish)."""
    rates = _rates(model)
    if rates is None:
        logger.debug("no pricing for model=%r; cost counted as 0", model)
        return 0.0
    in_rate, out_rate = rates
    cost = (input_tokens * in_rate + output_tokens * out_rate) / _PER_MILLION
    return round(cost, 6)
