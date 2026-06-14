"""Stripe payment endpoints (work for logged-in users and guest sessions).

  POST /payments/create-intent  — CSRF: create Order in pending_payment, make PI
  POST /payments/webhook         — no auth, raw body, Stripe-signature-verified
  POST /payments/confirm/{id}    — CSRF: re-fetch PI from Stripe, trust its status
  GET  /payments/status/{id}     — return Order payment_status + order_status
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Actor, get_actor, require_manager
from app.core.errors import NotFoundError
from app.core.security import verify_csrf
from app.services import audit_service, payment_service
from app.services.order_service import create_pending_order, get_order

router = APIRouter(prefix="/payments", tags=["payments"])


class CreateIntentBody(BaseModel):
    notes: str | None = None
    guest_email: str | None = None


class RefundBody(BaseModel):
    amount_cents: int | None = None  # omit for a full refund


def _own_order_or_404(db: Session, order_id: str, actor: Actor):
    order = get_order(db, order_id)
    if not actor.owns(user_id=order.user_id, session_id=order.session_id):
        raise NotFoundError("Order")
    return order


@router.post("/create-intent", dependencies=[Depends(verify_csrf)])
def create_intent(body: CreateIntentBody, actor: Actor = Depends(get_actor),
                  db: Session = Depends(get_db)):
    from app.core.config import settings

    # Fail fast if Stripe isn't configured, BEFORE creating a pending order.
    payment_service.ensure_configured()

    order = create_pending_order(db, actor.user_id, body.notes,
                                 session_id=actor.session_id, guest_email=body.guest_email)
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
def confirm_payment(order_id: str, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    order = _own_order_or_404(db, order_id, actor)
    pi_status = payment_service.confirm_by_order(db, order)
    db.refresh(order)
    return {"payment_status": order.payment_status, "order_status": order.status, "pi_status": pi_status}


@router.get("/status/{order_id}")
def payment_status(order_id: str, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    order = _own_order_or_404(db, order_id, actor)
    return {"payment_status": order.payment_status, "order_status": order.status, "order_id": order.id}


@router.post("/refund/{order_id}", dependencies=[Depends(verify_csrf)])
def refund_order(order_id: str, body: RefundBody | None = None,
                 user=Depends(require_manager), db: Session = Depends(get_db)):
    """Refund a paid order (manager/admin only). Full refund unless amount_cents is given."""
    order = get_order(db, order_id)  # 404s if missing
    result = payment_service.refund_order(
        db, order, amount_cents=(body.amount_cents if body else None)
    )
    audit_service.log(db, "payment_refund", actor_id=user.id, target=order.id, detail=result)
    return result
