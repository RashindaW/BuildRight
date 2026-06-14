"""Recommender service + product-page endpoint tests (DB-backed, seeded catalog)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem
from app.services.recommender_service import (
    frequently_bought_with,
    recommend_similar,
)


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _two_instock_items(db) -> tuple[MenuItem, MenuItem]:
    items = db.execute(
        select(MenuItem).where(MenuItem.is_available.is_(True), MenuItem.stock_qty > 0).limit(2)
    ).scalars().all()
    assert len(items) == 2
    return items[0], items[1]


def _make_order(db, *menu_items: MenuItem) -> Order:
    order = Order(
        order_number=f"REC-{uuid.uuid4().hex[:8]}",
        status="completed", subtotal_cents=0, total_cents=0, source="web",
    )
    db.add(order)
    db.flush()
    for mi in menu_items:
        db.add(OrderItem(
            order_id=order.id, menu_item_id=mi.id, name_snapshot=mi.name,
            unit_price_cents=mi.price_cents, quantity=1, line_total_cents=mi.price_cents,
        ))
    db.commit()
    return order


def test_frequently_bought_with_from_copurchases(db):
    a, b = _two_instock_items(db)
    # Two orders both containing A and B → B is co-bought with A.
    _make_order(db, a, b)
    _make_order(db, a, b)

    recs = frequently_bought_with(db, a.slug, k=5)
    slugs = [r["slug"] for r in recs]
    assert b.slug in slugs
    rec = next(r for r in recs if r["slug"] == b.slug)
    assert rec["score"] >= 2          # co-occurred in 2 orders
    assert "order" in rec["reason"]
    assert a.slug not in slugs        # never recommends the anchor itself


def test_frequently_bought_with_unknown_item(db):
    assert frequently_bought_with(db, "not-a-real-slug", k=5) == []


def test_recommend_similar_same_category(db):
    anchor = db.execute(
        select(MenuItem).where(MenuItem.is_available.is_(True), MenuItem.stock_qty > 0)
    ).scalars().first()
    recs = recommend_similar(db, anchor.slug, k=5)
    # Results (if any) are in the anchor's category and exclude the anchor.
    assert all(r["slug"] != anchor.slug for r in recs)
    if recs:
        anchor_cat = anchor.category.slug
        assert all(r["category"] == anchor_cat for r in recs)


def test_recommend_similar_by_sku(db):
    anchor = db.execute(
        select(MenuItem).where(MenuItem.sku.is_not(None), MenuItem.is_available.is_(True))
    ).scalars().first()
    assert recommend_similar(db, anchor.sku, k=3) is not None  # resolves by SKU, no error


def test_recommendations_endpoint(client, db):
    a, b = _two_instock_items(db)
    _make_order(db, a, b)
    r = client.get(f"/api/v1/menu/{a.slug}/recommendations")
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert all(item["slug"] != a.slug for item in data)
