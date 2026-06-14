"""Refund endpoint — RBAC + guards (no Stripe needed: guards run before the API call)."""

from __future__ import annotations

import uuid

import pytest

from app.core.db import SessionLocal
from app.models.order import Order


def _make_order(payment_status: str, *, paid_cents: int = 1000) -> str:
    db = SessionLocal()
    try:
        o = Order(
            order_number=f"RF-{uuid.uuid4().hex[:8]}",
            status="placed", subtotal_cents=paid_cents, total_cents=paid_cents,
            payment_status=payment_status, amount_paid_cents=paid_cents,
            stripe_payment_intent_id="pi_test_123", currency="cad",
        )
        db.add(o)
        db.commit()
        return o.id
    finally:
        db.close()


def test_refund_requires_manager(customer_client):
    oid = _make_order("paid")
    r = customer_client.post(f"/api/v1/payments/refund/{oid}")
    assert r.status_code == 403


def test_refund_unpaid_order_is_rejected(admin_client):
    oid = _make_order("unpaid")
    r = admin_client.post(f"/api/v1/payments/refund/{oid}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "not_refundable"


def test_refund_missing_order_404(admin_client):
    r = admin_client.post("/api/v1/payments/refund/does-not-exist")
    assert r.status_code == 404


def test_refund_paid_order_without_stripe_config(admin_client):
    # Order is 'paid' so it passes the app guard, then fails at Stripe config (503).
    oid = _make_order("paid")
    r = admin_client.post(f"/api/v1/payments/refund/{oid}")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "stripe_not_configured"
