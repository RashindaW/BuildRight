from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def _guest_client(session_id: str) -> TestClient:
    """A TestClient acting as an anonymous guest: an x-session-id but no auth cookie."""
    c = TestClient(app)
    c.headers.update({"x-session-id": session_id})
    c.get("/api/v1/auth/csrf")  # sets the csrf cookie for write endpoints
    c.headers.update({"x-csrf-token": c.cookies.get("csrf_token")})
    return c


def test_cart_requires_session_or_auth(client):
    # No auth and no x-session-id -> cannot use the cart.
    assert client.get("/api/v1/cart").status_code == 401


def test_guest_cart_and_order(seeded_item):
    sid = uuid.uuid4().hex
    g = _guest_client(sid)

    assert g.get("/api/v1/cart").json()["item_count"] == 0
    r = g.post("/api/v1/cart/items", json={"menu_item_id": seeded_item["slug"], "quantity": 2})
    assert r.status_code == 200, r.text
    assert r.json()["item_count"] == 2

    o = g.post("/api/v1/orders", json={"guest_email": "guest@example.com"})
    assert o.status_code == 200, o.text
    body = o.json()
    assert body["guest_email"] == "guest@example.com"
    assert body["total_cents"] == seeded_item["price_cents"] * 2

    # guest can view their own order (same session)
    assert g.get(f"/api/v1/orders/{body['id']}").status_code == 200
    # guests have no order history list (login-only)
    assert g.get("/api/v1/orders").status_code == 401


def test_guest_cart_isolated_by_session(seeded_item):
    a = _guest_client(uuid.uuid4().hex)
    a.post("/api/v1/cart/items", json={"menu_item_id": seeded_item["slug"], "quantity": 1})
    assert a.get("/api/v1/cart").json()["item_count"] == 1
    # a different session sees an empty cart
    b = _guest_client(uuid.uuid4().hex)
    assert b.get("/api/v1/cart").json()["item_count"] == 0


def test_guest_order_idor(seeded_item, customer_client):
    a = _guest_client(uuid.uuid4().hex)
    a.post("/api/v1/cart/items", json={"menu_item_id": seeded_item["slug"], "quantity": 1})
    oid = a.post("/api/v1/orders", json={}).json()["id"]

    # a different guest session cannot read it
    b = _guest_client(uuid.uuid4().hex)
    assert b.get(f"/api/v1/orders/{oid}").status_code == 404
    # a logged-in (non-admin) customer cannot read a guest order
    assert customer_client.get(f"/api/v1/orders/{oid}").status_code == 404


def test_admin_can_view_guest_order(seeded_item, admin_client):
    g = _guest_client(uuid.uuid4().hex)
    g.post("/api/v1/cart/items", json={"menu_item_id": seeded_item["slug"], "quantity": 1})
    oid = g.post("/api/v1/orders", json={}).json()["id"]
    assert admin_client.get(f"/api/v1/orders/{oid}").status_code == 200
