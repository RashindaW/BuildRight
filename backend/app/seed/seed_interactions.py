"""Synthetic purchase interactions — a real user-item graph for the recommender / GNN.

The catalog generator makes product *nodes* but no *edges*: the only real orders are a
handful of demo ones, which is far too sparse and low-entropy to train a graph model on.
This module deterministically generates realistic baskets (co-purchases biased by
cross-category affinity), giving both the co-occurrence recommender and the GNN a genuine
graph to learn from. Pure + seeded, so re-seeding is reproducible; idempotent.
"""

from __future__ import annotations

import logging
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu import Category, MenuItem
from app.models.order import Order, OrderItem

logger = logging.getLogger("app.seed.seed_interactions")

# Categories that tend to be bought together — each cluster is a shopper "persona".
_AFFINITY_CLUSTERS = [
    ["power-tools", "hand-tools", "fasteners", "building-materials", "safety"],
    ["paint", "building-materials", "hand-tools", "safety", "cleaning"],
    ["plumbing", "electrical", "hand-tools", "lighting", "safety"],
    ["outdoor", "lawn-garden", "seasonal", "safety"],
    ["cleaning", "kitchen", "storage"],
    ["flooring", "building-materials", "hand-tools", "safety"],
    ["automotive", "hand-tools", "cleaning"],
    ["lighting", "electrical", "storage", "hand-tools"],
]


def _items_by_category(db: Session) -> dict[str, list[MenuItem]]:
    rows = db.execute(
        select(MenuItem, Category.slug)
        .join(Category, Category.id == MenuItem.category_id)
        .where(MenuItem.is_available.is_(True))
    ).all()
    out: dict[str, list[MenuItem]] = {}
    for item, slug in rows:
        out.setdefault(slug, []).append(item)
    for pool in out.values():
        pool.sort(key=lambda i: i.slug)  # deterministic ordering before seeded sampling
    return out


def seed_interactions(db: Session, *, users: int = 60, seed: int = 2024) -> int:
    """Generate deterministic synthetic purchase baskets. Idempotent (skips if present)."""
    if db.execute(select(Order.id).where(Order.order_number.like("SYN-%")).limit(1)).first():
        return 0

    by_cat = _items_by_category(db)
    clusters = [[s for s in c if by_cat.get(s)] for c in _AFFINITY_CLUSTERS]
    clusters = [c for c in clusters if len(c) >= 2]
    if not clusters:
        return 0

    rng = random.Random(seed)
    n_orders = 0
    for u in range(users):
        cats = rng.choice(clusters)
        for o in range(rng.randint(1, 4)):
            basket_size = rng.randint(2, 5)
            chosen: list[MenuItem] = []
            seen: set[str] = set()
            for _ in range(basket_size):
                pool = by_cat.get(rng.choice(cats)) or []
                if not pool:
                    continue
                it = pool[rng.randrange(len(pool))]
                if it.id not in seen:
                    seen.add(it.id)
                    chosen.append(it)
            if len(chosen) < 2:
                continue

            order = Order(
                order_number=f"SYN-{u:04d}-{o}-{rng.randint(1000, 9999)}",
                session_id=f"syn-user-{u}",  # a stable pseudo-user for the bipartite graph
                status="completed",
                source="web",
                subtotal_cents=0,
                total_cents=0,
            )
            db.add(order)
            db.flush()
            subtotal = 0
            for it in chosen:
                line = it.price_cents
                subtotal += line
                db.add(OrderItem(
                    order_id=order.id, menu_item_id=it.id, name_snapshot=it.name,
                    unit_price_cents=it.price_cents, quantity=1, line_total_cents=line,
                ))
            order.subtotal_cents = subtotal
            order.total_cents = subtotal
            n_orders += 1

    db.commit()
    logger.info("seed_interactions: generated %d synthetic orders over %d users", n_orders, users)
    return n_orders
