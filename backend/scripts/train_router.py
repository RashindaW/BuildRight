"""Train the router difficulty head (pure NumPy — no sklearn) and commit the artifact.

    python -m scripts.train_router          # from backend/

Labels: 1 = the cheap model handles it well (simple lookups, single-fact questions);
0 = needs the heavy model (project planning, comparisons, multi-step math, vision).
The seed set below mirrors the eval-harness question styles + golden tests; telemetry
(route, guardrail passes, CSAT) can extend it as real traffic accumulates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.routing.difficulty import features_for  # noqa: E402

# (question, cheap_ok) — cheap_ok=1 for lookups the fast model nails.
SEED: list[tuple[str, int]] = [
    # --- simple product lookups / availability / price (cheap ok) ---
    ("Do you have cordless drills?", 1),
    ("How much is the cheapest hammer?", 1),
    ("Where are the screwdrivers?", 1),
    ("Do you sell duct tape?", 1),
    ("Is the circular saw in stock?", 1),
    ("Show me work gloves", 1),
    ("What LED bulbs do you carry?", 1),
    ("price of a 20V drill battery", 1),
    ("do you have snow shovels", 1),
    ("Any deals on paint brushes?", 1),
    ("I need a garden hose", 1),
    ("got any wd-40?", 1),
    ("do you carry Mastercraft?", 1),
    ("cheapest ladder you have", 1),
    ("Do you sell laser levels?", 1),
    ("where can I find sandpaper", 1),
    ("what plungers do you stock", 1),
    ("Do you have a 10mm socket?", 1),
    ("looking for a tape measure", 1),
    ("extension cords?", 1),
    # --- simple policy lookups (cheap ok) ---
    ("What's your return policy?", 1),
    ("Do you price match?", 1),
    ("How long is the warranty on power tools?", 1),
    ("What are your shipping options?", 1),
    ("Can I return an opened item?", 1),
    ("when do refunds arrive", 1),
    ("do you deliver?", 1),
    # --- reorders / account simple (cheap ok) ---
    ("Reorder my last paint order", 1),
    ("add that drill to my cart again", 1),
    ("what did I buy last month", 1),
    # --- project planning: measurements, quantities, multi-step (needs heavy) ---
    ("I want to paint my bedroom, it's 12 by 10 feet with 8 foot walls. What do I need?", 0),
    ("How much paint do I need for a 12x10 room?", 0),
    ("Planning to tile my 8x6 bathroom floor, what should I buy?", 0),
    ("I'm laying laminate in a 15 by 12 living room, help me plan it", 0),
    ("How many drywall sheets for a 20x12 room with 9 foot ceilings?", 0),
    ("I want to build a 10x12 deck, what materials and how much will it cost?", 0),
    ("renovating my kitchen — walk me through what I need to redo the backsplash", 0),
    ("Estimate materials to fence a 40 foot yard", 0),
    ("how much grout and thinset for 90 square feet of tile", 0),
    ("My basement is 30 by 20, how much insulation do I need?", 0),
    ("What will it cost to repaint two 14x12 rooms with primer and two coats?", 0),
    ("Help me plan a drywall repair for a 4 foot hole", 0),
    # --- comparisons / buying advice (needs heavy) ---
    ("What's the difference between an impact driver and a hammer drill?", 0),
    ("Which should I get, a brad nailer or a finish nailer?", 0),
    ("Compare corded vs cordless circular saws for a beginner", 0),
    ("oil based vs water based polyurethane, which is better for floors?", 0),
    ("Which drill is best for concrete versus wood?", 0),
    ("Help me choose between latex and oil paint for trim", 0),
    ("what's better for a deck: screws or nails, and which exact ones?", 0),
    ("MDF vs plywood for shelving, and what thickness should I buy?", 0),
    # --- multi-constraint / reasoning (needs heavy) ---
    ("I have a $200 budget: put together a starter toolkit for an apartment", 0),
    ("What do I need to childproof a house with stairs and a fireplace?", 0),
    ("My faucet leaks at the base and the handle sticks, what parts and tools do I need?", 0),
    ("Design a storage setup for a one-car garage with bikes and tools", 0),
    ("It's -20 outside and my pipes froze, what do I buy right now and in what order?", 0),
]


def train(x: np.ndarray, y: np.ndarray, *, lr: float = 0.3, epochs: int = 800, l2: float = 1e-3):
    w = np.zeros(x.shape[1])
    b = 0.0
    n = len(y)
    for _ in range(epochs):
        z = x @ w + b
        p = 1.0 / (1.0 + np.exp(-z))
        g = p - y
        w -= lr * ((x.T @ g) / n + l2 * w)
        b -= lr * float(g.mean())
    return w, b


def main() -> None:
    xs = np.asarray([features_for(q) for q, _ in SEED], dtype=np.float64)
    ys = np.asarray([lab for _, lab in SEED], dtype=np.float64)

    # Leave-one-out accuracy — honest for a tiny seed set.
    correct = 0
    for i in range(len(ys)):
        mask = np.arange(len(ys)) != i
        w, b = train(xs[mask], ys[mask])
        p = 1.0 / (1.0 + np.exp(-(xs[i] @ w + b)))
        correct += int((p >= 0.5) == bool(ys[i]))
    loo_acc = correct / len(ys)

    w, b = train(xs, ys)
    out = {
        "version": "router_head_v1",
        "embedding": "hash-bow-v1",
        "feature_dim": int(xs.shape[1]),
        "train_examples": len(ys),
        "loo_accuracy": round(loo_acc, 4),
        "weights": [round(float(v), 6) for v in w],
        "bias": round(float(b), 6),
    }
    dest = Path(__file__).resolve().parents[1] / "app" / "ai" / "routing" / "artifacts" / "router_head_v1.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out), encoding="utf-8")
    print(f"trained on {len(ys)} examples | LOO accuracy {loo_acc:.2%} | -> {dest}")


if __name__ == "__main__":
    main()
