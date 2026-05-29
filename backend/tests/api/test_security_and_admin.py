from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_security_headers_present(client):
    r = client.get("/api/v1/menu")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "X-Request-ID" in r.headers


def test_admin_endpoints_require_admin(customer_client):
    # A logged-in customer must be forbidden from admin routes
    r = customer_client.post("/api/v1/admin/menu", json={
        "slug": "hack", "name": "Hack", "price_cents": 100, "category": "drink"})
    assert r.status_code == 403


def test_admin_endpoints_require_auth(client):
    assert client.get("/api/v1/admin/orders").status_code == 401


def test_admin_can_create_and_delete_item(admin_client):
    slug = f"test-item-{uuid.uuid4().hex[:6]}"
    r = admin_client.post("/api/v1/admin/menu", json={
        "slug": slug, "name": "Test Item", "price_cents": 500,
        "category": "drink", "dietary_tags": ["vegan"]})
    assert r.status_code == 201, r.text
    assert r.json()["dietary_tags"] == ["vegan"]
    item_id = r.json()["id"]

    d = admin_client.delete(f"/api/v1/admin/menu/{item_id}")
    assert d.status_code == 200


def test_admin_lists_orders(admin_client):
    assert admin_client.get("/api/v1/admin/orders").status_code == 200


def test_health_ready(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["db"] is True


def test_unknown_route_no_stack_trace(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    assert "Traceback" not in r.text
