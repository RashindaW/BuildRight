"""GET /chat/memory — surfaces saved preferences for the logged-in user."""

from __future__ import annotations

from app.core.db import SessionLocal
from app.services.memory_service import set_preference


def test_memory_anonymous_is_empty(client):
    r = client.get("/api/v1/chat/memory")
    assert r.status_code == 200
    assert r.json() == {"preferences": {}, "recent_summaries": []}


def test_memory_returns_saved_preferences(customer_client):
    user_id = customer_client.get("/api/v1/auth/me").json()["id"]
    db = SessionLocal()
    try:
        set_preference(db, user_id, "preferred_brand", "Mastercraft")
    finally:
        db.close()
    r = customer_client.get("/api/v1/chat/memory")
    assert r.status_code == 200, r.text
    assert r.json()["preferences"].get("preferred_brand") == "Mastercraft"
