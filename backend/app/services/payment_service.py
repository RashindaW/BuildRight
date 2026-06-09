"""Stripe test-mode payment service.

Design notes:
- create_payment_intent: creates (or reuses) a Stripe PaymentIntent and persists its id.
- handle_webhook: verifies signature, marks Order paid/failed. Idempotent.
- confirm_by_order: re-fetches PaymentIntent from Stripe (source of truth) — local-dev
  path that avoids needing a tunnel for webhooks. NEVER trusts client-claimed status.

Money safety: _mark_paid validates the Stripe amount and currency against the order
before marking it paid, so an underpaid or wrong-currency intent can never settle an order.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger("app.services.payment")

# Terminal payment states that must never be downgraded by a late/replayed webhook.
_TERMINAL_PAID = ("paid", "refunded")


def ensure_configured() -> None:
    """Raise 503 if Stripe isn't configured. Call this BEFORE creating a pending
    order so a misconfigured deployment doesn't leave orphan pending_payment orders."""
    if not settings.stripe_secret_key.get_secret_value():
        raise AppError("Stripe is not configured — set STRIPE_SECRET_KEY", "stripe_not_configured", 503)


def _stripe():
    import stripe as _stripe_module
    ensure_configured()
    _stripe_module.api_key = settings.stripe_secret_key.get_secret_value()
    return _stripe_module


def create_payment_intent(db: Session, order) -> object:
    """Create (or reuse) a Stripe PaymentIntent for the order and persist its id.

    Reuse: if the order already carries a PaymentIntent (e.g. the user double-clicked
    or retried), the existing intent is retrieved rather than creating a duplicate.
    A stable idempotency_key gives Stripe-side dedup as a second line of defense.
    """
    stripe = _stripe()

    # Record the currency the intent is actually created in (source of truth).
    order.currency = settings.stripe_currency.lower()

    if order.stripe_payment_intent_id:
        intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
        # Only reuse a still-payable intent; otherwise fall through to create a new one.
        if intent.status not in ("canceled", "succeeded"):
            db.commit()
            logger.info("payment_intent_reused: order=%s intent=%s", order.id, intent.id)
            return intent

    intent = stripe.PaymentIntent.create(
        amount=order.total_cents,
        currency=order.currency,
        metadata={
            "order_id": order.id,
            "order_number": order.order_number,
        },
        idempotency_key=f"pi_create_{order.id}",
    )
    order.stripe_payment_intent_id = intent.id
    db.commit()
    logger.info("payment_intent_created: order=%s intent=%s", order.id, intent.id)
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

    # Bind the Stripe intent to the authorized order: the caller was authorized for
    # `order` (router checks order.user_id == user.id), so refuse to act if the
    # intent's metadata names a different order than the one we hold.
    meta_order_id = (pi.get("metadata") or {}).get("order_id")
    if meta_order_id and meta_order_id != order.id:
        raise AppError("Payment intent does not match order", "intent_order_mismatch", 409)

    if pi.status == "succeeded":
        _mark_paid(db, pi, order=order)
    elif pi.status in ("canceled", "requires_payment_method"):
        _mark_failed(db, pi, order=order)
    return pi.status


# ---- Internal helpers ----------------------------------------------------

def _resolve_order(db: Session, pi, order):
    """Use the caller-authorized order on the confirm path; otherwise (webhook)
    derive it from the intent metadata."""
    if order is not None:
        return order
    from app.models.order import Order
    order_id = (pi.get("metadata") or {}).get("order_id")
    if not order_id:
        logger.warning("payment_event_without_order_id: intent=%s", pi.get("id"))
        return None
    return db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()


def _mark_paid(db: Session, pi, order=None) -> None:
    from app.models.cart import Cart

    order = _resolve_order(db, pi, order)
    if not order or order.payment_status == "paid":
        return

    # --- Money guard: never settle an order on an underpaid or wrong-currency intent ---
    amount = pi.get("amount_received") or pi.get("amount") or 0
    pi_currency = (pi.get("currency") or "").lower()
    order_currency = (order.currency or "").lower()
    if amount < order.total_cents or pi_currency != order_currency:
        logger.warning(
            "payment_amount_mismatch: order=%s expected=%s/%s got=%s/%s",
            order.id, order.total_cents, order_currency, amount, pi_currency,
        )
        return  # leave order untouched for manual review
    # --- end money guard ---

    order.payment_status = "paid"
    order.status = "placed"
    order.amount_paid_cents = amount

    # Convert the exact cart this order was derived from (not "whatever is active now").
    if order.cart_id:
        cart = db.execute(select(Cart).where(Cart.id == order.cart_id)).scalar_one_or_none()
        if cart and cart.status == "active":
            cart.status = "converted"

    db.commit()
    logger.info("payment_succeeded: order=%s", order.id)


def _mark_failed(db: Session, pi, order=None) -> None:
    order = _resolve_order(db, pi, order)
    if not order:
        return
    # Never downgrade a successful/refunded payment to failed — Stripe webhooks are
    # unordered and can be replayed.
    if order.payment_status in _TERMINAL_PAID:
        return

    order.payment_status = "failed"
    db.commit()
    logger.info("payment_failed: order=%s", order.id)
