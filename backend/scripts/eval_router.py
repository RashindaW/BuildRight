"""Router v2 evaluation — held-out routing accuracy + the cost-quality frontier.

    python -m scripts.eval_router      # prints + writes app/ai/routing/router_metrics.json

The holdout set below is DISJOINT from scripts/train_router.py's seed set. "Optimal"
means: cheap-ok questions should route to a fast-class model, heavy-needed questions to
a heavy-class model. The frontier sweeps the three router policies (λ values).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.registry import registry  # noqa: E402
from app.ai.routing import policy  # noqa: E402
from app.core.config import settings  # noqa: E402

# (question, cheap_ok) — none of these appear in the training seed.
HOLDOUT: list[tuple[str, int]] = [
    ("do you stock zip ties", 1),
    ("How much is a shop vac?", 1),
    ("do you have caulk guns in stock", 1),
    ("looking for a stud finder", 1),
    ("Do you sell dehumidifiers?", 1),
    ("what's the price of a chalk line", 1),
    ("any cordless leaf blowers?", 1),
    ("do you carry DeWalt batteries", 1),
    ("Can I return paint?", 1),
    ("how long do refunds take to process", 1),
    ("do you offer curbside pickup", 1),
    ("reorder the sandpaper from my last order", 1),
    ("I'm finishing my 16 by 14 basement, what materials do I need and what will it cost?", 0),
    ("How many boxes of laminate for 220 square feet with waste?", 0),
    ("Plan the paint and primer for a hallway 30 feet long with 9 foot ceilings", 0),
    ("what do I need to drywall a 12x14 garage ceiling", 0),
    ("Compare framing nailers vs finish nailers for baseboard work", 0),
    ("impact wrench versus impact driver, which do I need for lug nuts?", 0),
    ("Which sander should I get for refinishing a hardwood table, and what grits?", 0),
    ("I have $150: assemble a plumbing emergency kit for a rental unit", 0),
    ("My deck boards are cupping and two joists feel soft, what's my repair plan?", 0),
    ("Design shelving for a 8x10 shed to hold paint, tools and two bikes", 0),
]


def main() -> None:
    registry.reload()
    results = {}
    for pol in ("economy", "balanced", "quality"):
        settings.router_policy = pol
        correct = 0
        est_cost = 0.0
        heavy_cost = 0.0
        for q, cheap_ok in HOLDOUT:
            d = policy.decide(q)
            assert d is not None
            e = registry.get(d.model_id)
            is_fast = e.latency_class != "heavy"
            correct += int(is_fast == bool(cheap_ok))
            est_cost += d.est_cost_per_turn
            heavy_cost += policy._est_cost(registry.get(settings.llm_model_heavy))
        results[pol] = {
            "optimal_choice_acc": round(correct / len(HOLDOUT), 4),
            "est_cost_per_100_turns": round(est_cost / len(HOLDOUT) * 100, 4),
            "always_heavy_cost_per_100_turns": round(heavy_cost / len(HOLDOUT) * 100, 4),
            "cost_saved_pct": round((1 - est_cost / heavy_cost) * 100, 1) if heavy_cost else 0,
        }
    settings.router_policy = "balanced"

    out = {"holdout_examples": len(HOLDOUT), "policies": results}
    dest = Path(__file__).resolve().parents[1] / "app" / "ai" / "routing" / "router_metrics.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
