"""Recommender evaluation — recall@k over held-out co-purchases.

Protocol: for every co-purchase pair (a, b) drawn from the order baskets, ask the
recommender for `a` and check whether `b` appears in the top-k. recall@k is the fraction
of pairs recovered. We report the GNN/graph recommender against the co-occurrence baseline
so the graph model's lift is *measured*, not assumed.

    python -m app.ai.eval.recommender_eval     # prints + writes recommender_metrics.json
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu import MenuItem
from app.models.order import OrderItem

logger = logging.getLogger("app.ai.eval.recommender_eval")

_OUT = Path(__file__).with_name("recommender_metrics.json")


def _copurchase_pairs(db: Session) -> list[tuple[str, str]]:
    baskets: dict[str, list[str]] = {}
    for oid, mid in db.execute(select(OrderItem.order_id, OrderItem.menu_item_id)).all():
        if mid:
            baskets.setdefault(oid, []).append(mid)
    pairs: list[tuple[str, str]] = []
    for items in baskets.values():
        uniq = list(dict.fromkeys(items))
        for i in range(len(uniq)):
            for j in range(len(uniq)):
                if i != j:
                    pairs.append((uniq[i], uniq[j]))
    return pairs


def evaluate(db: Session, *, k: int = 5, sample: int = 400, seed: int = 0) -> dict:
    from app.ai.recommend.gnn import graph_recommend
    from app.services.recommender_service import frequently_bought_with

    id2slug = dict(db.execute(select(MenuItem.id, MenuItem.slug)).all())
    pairs = _copurchase_pairs(db)
    if not pairs:
        return {"k": k, "pairs": 0, "graph_recall": 0.0, "cooccurrence_recall": 0.0}

    rng = random.Random(seed)
    rng.shuffle(pairs)
    pairs = pairs[:sample]

    def recall(fn) -> float:
        hits = total = 0
        for a, b in pairs:
            b_slug = id2slug.get(b)
            if not b_slug:
                continue
            total += 1
            if any(r.get("slug") == b_slug for r in fn(db, a, k)):
                hits += 1
        return round(hits / total, 4) if total else 0.0

    return {
        "k": k,
        "pairs": len(pairs),
        "graph_recall": recall(graph_recommend),
        "cooccurrence_recall": recall(frequently_bought_with),
    }


def main() -> None:
    from app.core.db import SessionLocal

    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        metrics = {f"recall@{k}": evaluate(db, k=k) for k in (5, 10)}
    finally:
        db.close()
    _OUT.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
