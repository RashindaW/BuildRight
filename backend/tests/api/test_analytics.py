from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def _manager_client() -> TestClient:
    """A TestClient authenticated as a manager (created directly in the test DB)."""
    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    email = f"mgr-{uuid.uuid4().hex[:8]}@example.com"
    db = SessionLocal()
    db.add(User(email=email, hashed_password=hash_password("Password123!"),
                full_name="Mgr", role="manager", is_active=True))
    db.commit()
    db.close()
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert r.status_code == 200, r.text
    c.headers.update({"x-csrf-token": c.cookies.get("csrf_token")})
    return c


def test_analytics_requires_manager(customer_client):
    assert customer_client.get("/api/v1/analytics/inventory").status_code == 403
    assert customer_client.get("/api/v1/analytics/margins").status_code == 403
    assert customer_client.get("/api/v1/analytics/ai-attribution").status_code == 403


def test_analytics_requires_auth(client):
    assert client.get("/api/v1/analytics/inventory").status_code == 401


def test_inventory_summary(client_unused=None):
    c = _manager_client()
    d = c.get("/api/v1/analytics/inventory").json()
    assert d["total_products"] > 0
    assert d["in_stock"] + d["out_of_stock"] == d["total_products"]
    assert isinstance(d["low_stock"], list) and isinstance(d["by_category"], list)
    assert d["inventory_value_retail_cents"] >= d["inventory_value_cost_cents"] > 0


def test_margins_and_attribution(customer_client, seeded_item):
    # place a normal (web) order
    customer_client.post("/api/v1/cart/items",
                         json={"menu_item_id": seeded_item["slug"], "quantity": 2})
    o = customer_client.post("/api/v1/orders", json={})
    assert o.status_code == 200, o.text

    mgr = _manager_client()
    m = mgr.get("/api/v1/analytics/margins?days=365").json()
    assert m["overall"]["revenue_cents"] >= seeded_item["price_cents"] * 2
    assert m["overall"]["gross_profit_cents"] <= m["overall"]["revenue_cents"]
    assert 0 <= m["overall"]["margin_pct"] <= 100

    a = mgr.get("/api/v1/analytics/ai-attribution?days=365").json()
    assert a["total_orders"] >= 1
    assert 0 <= a["chat_orders"] <= a["total_orders"]
