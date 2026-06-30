"""Admin create/update embeds the product immediately (enters vector search without reseed)."""

from __future__ import annotations

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.product_embedding import ProductEmbedding


def test_admin_create_item_embeds_it(admin_client):
    cats = admin_client.get("/api/v1/menu/categories").json()
    assert cats, "need at least one category"
    payload = {
        "slug": "test-embed-widget",
        "name": "Test Embed Widget",
        "description": "A widget created to verify embed-on-add.",
        "price_cents": 1999,
        "category": cats[0]["slug"],
        "keywords": ["widget", "embed", "test"],
    }
    r = admin_client.post("/api/v1/admin/menu", json=payload)
    assert r.status_code == 201, r.text
    item_id = r.json()["id"]

    db = SessionLocal()
    try:
        emb = db.execute(
            select(ProductEmbedding).where(ProductEmbedding.menu_item_id == item_id)
        ).scalar_one_or_none()
    finally:
        db.close()
    assert emb is not None, "new item should be embedded on create"
    assert emb.embedding is not None
