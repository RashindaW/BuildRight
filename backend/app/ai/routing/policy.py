"""Router v2 decision policy — constraint filter → predicted quality → cost-aware pick.

decide() is pure and zero-latency (no LLM call): the difficulty head runs in NumPy and
candidates come from the registry. Selection maximizes `quality − λ·cost`, where λ is
set by `router_policy` (economy | balanced | quality).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.ai.registry import ModelEntry, registry
from app.ai.routing.difficulty import p_cheap_ok
from app.core.config import settings

logger = logging.getLogger("app.ai.routing")

# λ: how many quality-points one normalized cost-point is worth trading away.
_LAMBDA = {"economy": 0.5, "balanced": 0.25, "quality": 0.08}

# Quality prior by latency class: heavies are assumed to handle (almost) anything;
# a fast model's expected quality is the head's P(cheap-ok) scaled by its prior.
_CLASS_PRIOR = {"heavy": 0.98, "balanced": 0.92, "fast": 0.90}


@dataclass
class RouteDecision:
    model_id: str
    label: str                  # simple | complex | multimodal (telemetry-compatible)
    predicted_difficulty: float  # 1 - P(cheap ok)
    candidates: int
    est_cost_per_turn: float    # rough $ estimate for badges
    router_version: str = "v2"


def _est_cost(e: ModelEntry, in_tokens: int = 2500, out_tokens: int = 350) -> float:
    """Rough per-turn cost at typical token volumes (for ranking + UI badges)."""
    return (in_tokens * e.price_in + out_tokens * e.price_out) / 1_000_000


def decide(question: str, has_image: bool = False, turn_index: int = 0) -> RouteDecision | None:
    """Pick a model, or None when no registry candidates exist (caller falls back)."""
    capability = "vision" if has_image else "tools"
    candidates = registry.routable(capability)
    if not candidates:
        return None

    p_ok = p_cheap_ok(question, has_image=has_image, turn_index=turn_index)
    difficulty = 1.0 - p_ok
    lam = _LAMBDA.get(settings.router_policy, _LAMBDA["balanced"])

    costs = [_est_cost(e) for e in candidates]
    max_cost = max(costs) or 1.0

    best, best_score = None, -1e9
    for e, cost in zip(candidates, costs):
        prior = _CLASS_PRIOR.get(e.latency_class, 0.9)
        # Heavies handle ~anything; a fast model's expected quality is the head's
        # P(cheap-ok), capped by its class prior.
        quality = prior if e.latency_class == "heavy" else min(p_ok, prior)
        score = quality - lam * (cost / max_cost)
        if score > best_score:
            best, best_score = e, score

    label = "multimodal" if has_image else ("complex" if difficulty >= 0.5 else "simple")
    return RouteDecision(
        model_id=best.id,
        label=label,
        predicted_difficulty=round(difficulty, 3),
        candidates=len(candidates),
        est_cost_per_turn=round(_est_cost(best), 5),
    )


def strongest_healthy(exclude: str = "") -> str | None:
    """The heaviest healthy tools-capable model (cascade escalation target)."""
    pool = [e for e in registry.routable("tools") if e.id != exclude]
    if not pool:
        return None
    pool.sort(key=lambda e: (e.latency_class != "heavy", _est_cost(e)))
    return pool[0].id
