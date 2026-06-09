"""Stripe payment endpoints.

  POST /payments/create-intent  — auth+CSRF: create Order in pending_payment, make PI
  POST /payments/webhook         — no auth, raw body, Stripe-signature-verified
  POST /payments/confirm/{id}    — auth+CSRF: re-fetch PI from Stripe, trust its status
  GET  /payments/status/{id}     — auth: return Order payment_status + order_status
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.core.security import verify_csrf
from app.services import payment_service
from app.services.order_service import create_pending_order, get_order

router = APIRouter(prefix="/payments", tags=["payments"])


class CreateIntentBody(BaseModel):
    notes: str | None = None


@router.post("/create-intent", dependencies=[Depends(verify_csrf)])
def create_intent(
    body: CreateIntentBody,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.core.config import settings

    # Fail fast if Stripe isn't configured, BEFORE creating a pending order —
    # otherwise a misconfigured deployment accrues orphan pending_payment orders.
    payment_service.ensure_configured()

    order = create_pending_order(db, user.id, body.notes)
    intent = payment_service.create_payment_intent(db, order)
    return {
        "client_secret": intent.client_secret,
        "order_id": order.id,
        "publishable_key": settings.stripe_publishable_key,
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    payload = await request.body()
    event_type = payment_service.handle_webhook(db, payload, stripe_signature)
    return {"received": True, "type": event_type}


@router.post("/confirm/{order_id}", dependencies=[Depends(verify_csrf)])
def confirm_payment(
    order_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    order = get_order(db, order_id)
    if order.user_id != user.id:
        raise NotFoundError("Order")
    pi_status = payment_service.confirm_by_order(db, order)
    db.refresh(order)
    return {
        "payment_status": order.payment_status,
        "order_status": order.status,
        "pi_status": pi_status,
    }


@router.get("/status/{order_id}")
def payment_status(
    order_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    order = get_order(db, order_id)
    if order.user_id != user.id:
        raise NotFoundError("Order")
    return {
        "payment_status": order.payment_status,
        "order_status": order.status,
        "order_id": order.id,
    }
