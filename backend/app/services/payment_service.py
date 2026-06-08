"""Stripe test-mode payment service.

Design notes:
- create_payment_intent: creates a Stripe PaymentIntent and persists its id on the Order.
- handle_webhook: verifies signature, marks Order paid/failed. Idempotent.
- confirm_by_order: re-fetches PaymentIntent from Stripe (source of truth) — local-dev
  path that avoids needing a tunnel for webhooks. NEVER trusts client-claimed status.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger("app.services.payment")


def _stripe():
    import stripe as _stripe_module
    key = settings.stripe_secret_key.get_secret_value()
    if not key:
        raise AppError("Stripe is not configured — set STRIPE_SECRET_KEY", "stripe_not_configured", 503)
    _stripe_module.api_key = key
    return _stripe_module


def create_payment_intent(db: Session, order) -> object:
    """Create a Stripe PaymentIntent for the order and persist the intent id."""
    stripe = _stripe()
    intent = stripe.PaymentIntent.create(
        amount=order.total_cents,
        currency=settings.stripe_currency,
        metadata={
            "order_id": order.id,
            "order_number": order.order_number,
        },
    )
    order.stripe_payment_intent_id = intent.id
    db.commit()
    logger.info('"payment_intent_created: order=%s intent=%s"', order.id, intent.id)
    return intent


def handle_webhook(db: Session, payload: bytes, sig_header: str) -> str:
    """Verify Stripe webhook signature and apply the event. Returns the event type."""
    stripe = _stripe()
    secret = settings.stripe_webhook_secret.get_secret_value()
    if not secret:
        raise AppError("Stripe webhook secret not configured", "stripe_not_configured", 503)
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except stripe.error.SignatureVerificationError:
        raise AppError("Invalid webhook signature", "invalid_signature", 400)

    if event["type"] == "payment_intent.succeeded":
        _mark_paid(db, event["data"]["object"])
    elif event["type"] == "payment_intent.payment_failed":
        _mark_failed(db, event["data"]["object"])

    return event["type"]


def confirm_by_order(db: Session, order) -> str:
    """Re-fetch the PaymentIntent from Stripe and apply its current status.

    Used for local dev (no tunnel) — the frontend calls this after
    stripe.confirmPayment resolves. Returns the Stripe PI status string.
    """
    stripe = _stripe()
    if not order.stripe_payment_intent_id:
        raise AppError("No payment intent associated with this order", "no_intent", 400)
    pi = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
    if pi.status == "succeeded":
        _mark_paid(db, pi)
    elif pi.status in ("canceled", "requires_payment_method"):
        _mark_failed(db, pi)
    return pi.status


# ---- Internal helpers ----------------------------------------------------

def _mark_paid(db: Session, pi) -> None:
    from sqlalchemy import select
    from app.models.order import Order
    from app.models.cart import Cart

    order_id = (pi.get("metadata") or {}).get("order_id")
    if not order_id:
        return
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if not order or order.payment_status == "paid":
        return

    order.payment_status = "paid"
    order.status = "placed"
    order.amount_paid_cents = pi.get("amount_received") or pi.get("amount") or 0

    cart = db.execute(
        select(Cart).where(Cart.user_id == order.user_id, Cart.status == "active")
    ).scalar_one_or_none()
    if cart:
        cart.status = "converted"

    db.commit()
    logger.info('"payment_succeeded: order=%s"', order_id)


def _mark_failed(db: Session, pi) -> None:
    from sqlalchemy import select
    from app.models.order import Order

    order_id = (pi.get("metadata") or {}).get("order_id")
    if not order_id:
        return
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if not order:
        return

    order.payment_status = "failed"
    db.commit()
    logger.info('"payment_failed: order=%s"', order_id)
