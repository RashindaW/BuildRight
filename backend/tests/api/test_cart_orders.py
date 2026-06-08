from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_cart_requires_auth(client):
    assert client.get("/api/v1/cart").status_code == 401


def test_add_to_cart_and_total(customer_client, seeded_item):
    r = customer_client.post("/api/v1/cart/items",
                             json={"menu_item_id": seeded_item["slug"], "quantity": 2})
    assert r.status_code == 200, r.text
    cart = r.json()
    assert cart["item_count"] == 2
    assert cart["subtotal_cents"] == seeded_item["price_cents"] * 2


def test_csrf_required_for_cart_write():
    c = TestClient(app)
    email = f"x-{uuid.uuid4().hex[:8]}@example.com"
    c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    # no CSRF header attached
    r = c.post("/api/v1/cart/items", json={"menu_item_id": "classic-latte", "quantity": 1})
    assert r.status_code == 403


def test_checkout_creates_order_with_snapshot(customer_client, seeded_item):
    customer_client.post("/api/v1/cart/items",
                         json={"menu_item_id": seeded_item["slug"], "quantity": 1})
    r = customer_client.post("/api/v1/orders", json={})
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["order_number"].startswith("CD-")
    assert order["total_cents"] == seeded_item["price_cents"]
    assert order["items"][0]["name_snapshot"] == seeded_item["name"]
    assert order["status"] == "placed"


def test_empty_cart_checkout_rejected(customer_client):
    r = customer_client.post("/api/v1/orders", json={})
    assert r.status_code == 400


def test_idor_other_users_order_is_404(seeded_item):
    # User A places an order
    a = TestClient(app)
    ea = f"a-{uuid.uuid4().hex[:8]}@example.com"
    a.post("/api/v1/auth/register", json={"email": ea, "password": "Password123!"})
    a.headers.update({"x-csrf-token": a.cookies.get("csrf_token")})
    a.post("/api/v1/cart/items", json={"menu_item_id": seeded_item["slug"], "quantity": 1})
    order_id = a.post("/api/v1/orders", json={}).json()["id"]

    # User B must not be able to read it
    b = TestClient(app)
    eb = f"b-{uuid.uuid4().hex[:8]}@example.com"
    b.post("/api/v1/auth/register", json={"email": eb, "password": "Password123!"})
    r = b.get(f"/api/v1/orders/{order_id}")
    assert r.status_code == 404  # IDOR guard: not found, not 403 (no existence leak)
