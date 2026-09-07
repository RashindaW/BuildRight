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


def test_admin_can_create_and_delete_item(admin_client, seeded_item):
    slug = f"test-item-{uuid.uuid4().hex[:6]}"
    r = admin_client.post("/api/v1/admin/menu", json={
        "slug": slug, "name": "Test Item", "price_cents": 500,
        "category": seeded_item["category"], "dietary_tags": ["cordless"]})
    assert r.status_code == 201, r.text
    assert r.json()["dietary_tags"] == ["cordless"]
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


def test_health_ready_reports_knowledge_base_integrity(client):
    """An absent policy corpus has to be visible on the probe, not just in a log line."""
    body = client.get("/health/ready").json()
    kb = body["knowledge_base"]
    assert set(kb) == {"ok", "policy_documents", "by_type"}
    assert isinstance(kb["by_type"], dict)
    assert kb["ok"] == (kb["policy_documents"] > 0)
    # Non-production is NOT gated on it — dev/test run partially seeded all the time.
    assert body["status"] == "ready"


def test_health_ready_is_red_in_production_without_a_policy_corpus(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    r = client.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["status"] == "not_ready"
    assert r.json()["knowledge_base"]["ok"] is False
