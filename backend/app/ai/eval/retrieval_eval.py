"""Retrieval evaluation harness — recall/hit@k, MRR, nDCG over a labeled set.

Measures the hybrid retriever (lexical + vector → RRF, and any re-ranker) against a
hand-labeled question→relevant-doc set, so every retrieval change is *measured*, not
guessed. Pure metric functions (keyless, unit-tested) + live evaluators over the
seeded DB; `python -m app.ai.eval.retrieval_eval` writes a committed report.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

logger = logging.getLogger("app.ai.eval.retrieval")

_OUT = Path(__file__).resolve().parent / "retrieval_metrics.json"

# --- Labeled sets (question → set of acceptable target ids) ----------------

# KB: question → acceptable knowledge-base document slugs.
LABELED_KB: list[tuple[str, set[str]]] = [
    ("how long do I have to return a power tool", {"returns", "faq", "refund-policy-details"}),
    ("can I get a refund to my original payment method", {"refunds", "refund-policy-details"}),
    ("what does the manufacturer warranty cover", {"warranty"}),
    ("how much does shipping cost and how fast is it", {"shipping-delivery"}),
    ("do you match a competitor's price", {"price-match"}),
    ("can I finance a large purchase", {"financing-and-credit"}),
    ("do you sell gift cards", {"gift-cards"}),
    ("how do the rewards points work", {"rewards-program"}),
    ("has this product been recalled, is it safe", {"safety-and-recalls"}),
    ("do you offer assembly or installation", {"assembly-and-installation"}),
    ("how do I track or change my order", {"order-tracking-and-changes"}),
    ("do you have accounts for contractors", {"commercial-and-pro-accounts"}),
    ("how do I clean and maintain my tools", {"product-care-and-maintenance"}),
    ("what are your store hours and policies", {"store-policies", "faq"}),
]

# Products: question → acceptable product category slugs.
LABELED_PRODUCTS: list[tuple[str, set[str]]] = [
    ("a cordless drill for home use", {"power-tools"}),
    ("something to cut plywood", {"power-tools"}),
    ("interior wall paint", {"paint"}),
    ("a kitchen faucet", {"plumbing"}),
    ("led light bulbs", {"lighting", "electrical"}),
    ("wood screws and fasteners", {"fasteners", "hardware"}),
    ("a lawn mower", {"outdoor", "lawn-garden"}),
    ("safety glasses and gloves", {"safety"}),
    ("an extension cord", {"electrical"}),
    ("a claw hammer", {"hand-tools"}),
]


# --- Pure metric functions (unit-tested, no DB) ----------------------------

def _ranked_relevant_positions(ranked: list[str], relevant: set[str]) -> list[int]:
    """0-based positions in `ranked` (deduped, order-preserving) that are relevant."""
    seen, pos, out = set(), 0, []
    for r in ranked:
        if r in seen:
            continue
        seen.add(r)
        if r in relevant:
            out.append(pos)
        pos += 1
    return out


def hit_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """1.0 if any relevant target is in the top-k (deduped), else 0.0."""
    positions = _ranked_relevant_positions(ranked, relevant)
    return 1.0 if any(p < k for p in positions) else 0.0


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    positions = _ranked_relevant_positions(ranked, relevant)
    return 1.0 / (positions[0] + 1) if positions else 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Binary-relevance nDCG@k."""
    positions = [p for p in _ranked_relevant_positions(ranked, relevant) if p < k]
    dcg = sum(1.0 / math.log2(p + 2) for p in positions)
    ideal_n = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_n)) or 1.0
    return dcg / idcg


def aggregate(rankings: list[tuple[list[str], set[str]]], k: int = 5) -> dict:
    n = len(rankings) or 1
    return {
        f"hit@{k}": round(sum(hit_at_k(r, rel, k) for r, rel in rankings) / n, 4),
        "mrr": round(sum(reciprocal_rank(r, rel) for r, rel in rankings) / n, 4),
        f"ndcg@{k}": round(sum(ndcg_at_k(r, rel, k) for r, rel in rankings) / n, 4),
        "queries": len(rankings),
    }


# --- Live evaluators over the seeded DB ------------------------------------

def evaluate_kb(db, k: int = 5) -> dict:
    from app.ai.hybrid import hybrid_search_kb
    rankings = []
    for q, relevant in LABELED_KB:
        hits = hybrid_search_kb(db, q, k=max(k, 8))
        rankings.append(([h.doc_slug for h in hits], relevant))
    return aggregate(rankings, k)


def evaluate_products(db, k: int = 5) -> dict:
    from app.ai.hybrid import hybrid_search_products
    rankings = []
    for q, relevant in LABELED_PRODUCTS:
        items = hybrid_search_products(db, q, k=max(k, 8))
        rankings.append(([i.get("category", "") for i in items], relevant))
    return aggregate(rankings, k)


def main() -> None:
    from app.core.db import SessionLocal
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = {"kb": evaluate_kb(db), "products": evaluate_products(db)}
    finally:
        db.close()
    _OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nWrote {_OUT}")


if __name__ == "__main__":
    main()
