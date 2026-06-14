"""Recommender service — two lightweight, explainable signals the assistant and
the storefront can call:

- frequently_bought_with: item-item collaborative filtering from real order
  co-purchases (no model, no training — a co-occurrence count over OrderItem).
- recommend_similar: content-based similarity (same category, keyword overlap,
  price proximity) that works without trained embeddings.

Both return serialized item dicts (price in dollars, slug, sku) so callers can
ground prices through the existing guardrail. A GNN recommender is a future
upgrade (Phase 4.2b); these prove the surface first.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.menu import MenuItem
from app.models.order import OrderItem

_SCALE = 100  # cents → dollars


def _serialize(item: MenuItem, *, score: float, reason: str) -> dict:
    return {
        "id": item.slug,
        "slug": item.slug,
        "sku": item.sku,
        "name": item.name,
        "price": item.price_cents / _SCALE,
        "category": item.category.slug if item.category else None,
        "score": round(score, 4),
        "reason": reason,
    }


def _resolve(db: Session, item_ref: str) -> MenuItem | None:
    ref = (item_ref or "").strip()
    if not ref:
        return None
    return db.execute(
        select(MenuItem).where(
            (MenuItem.id == ref)
            | (MenuItem.slug == ref.lower())
            | (func.lower(MenuItem.sku) == ref.lower())
        )
    ).scalar_one_or_none()


def frequently_bought_with(db: Session, item_ref: str, k: int = 5) -> list[dict]:
    """Items most often appearing in the same orders as the anchor item.

    Pure co-occurrence CF: count distinct orders in which each other item appears
    alongside the anchor, rank by that count. Only in-stock items are returned.
    """
    anchor = _resolve(db, item_ref)
    if anchor is None:
        return []

    orders_with_anchor = (
        select(OrderItem.order_id)
        .where(OrderItem.menu_item_id == anchor.id)
        .scalar_subquery()
    )
    rows = db.execute(
        select(OrderItem.menu_item_id, func.count(func.distinct(OrderItem.order_id)))
        .where(
            OrderItem.order_id.in_(orders_with_anchor),
            OrderItem.menu_item_id.is_not(None),
            OrderItem.menu_item_id != anchor.id,
        )
        .group_by(OrderItem.menu_item_id)
        .order_by(func.count(func.distinct(OrderItem.order_id)).desc())
        .limit(k * 3)
    ).all()

    out: list[dict] = []
    for menu_item_id, co_count in rows:
        mi = db.get(MenuItem, menu_item_id)
        if mi is None or not mi.is_available or mi.stock_qty <= 0:
            continue
        out.append(_serialize(
            mi, score=float(co_count),
            reason=f"bought together in {co_count} order(s)",
        ))
        if len(out) >= k:
            break
    return out


def _keyword_overlap(a: MenuItem, b: MenuItem) -> float:
    sa, sb = set(a.keywords or []), set(b.keywords or [])
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)  # Jaccard


def recommend_similar(db: Session, item_ref: str, k: int = 5) -> list[dict]:
    """Content-based: same-category items ranked by keyword overlap + price
    proximity. Works without trained embeddings (robust to the hash fallback)."""
    anchor = _resolve(db, item_ref)
    if anchor is None:
        return []

    candidates = db.execute(
        select(MenuItem).where(
            MenuItem.category_id == anchor.category_id,
            MenuItem.id != anchor.id,
            MenuItem.is_available.is_(True),
            MenuItem.stock_qty > 0,
        ).limit(300)
    ).scalars().all()

    anchor_price = max(anchor.price_cents, 1)
    scored: list[tuple[float, MenuItem]] = []
    for c in candidates:
        kw = _keyword_overlap(anchor, c)
        price_gap = abs(c.price_cents - anchor_price) / anchor_price
        price_score = max(0.0, 1.0 - min(price_gap, 1.0))
        score = 0.7 * kw + 0.3 * price_score
        scored.append((score, c))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        _serialize(c, score=s, reason="similar item in the same category")
        for s, c in scored[:k]
    ]
