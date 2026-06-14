from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.db import get_db
from app.core.deps import Actor, get_actor, get_current_user
from app.core.errors import NotFoundError
from app.core.security import verify_csrf
from app.schemas.order import OrderCreateIn, OrderOut
from app.services import audit_service, order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, dependencies=[Depends(verify_csrf)])
def create_order(body: OrderCreateIn, request: Request,
                 actor: Actor = Depends(get_actor), db=Depends(get_db)):
    order = order_service.place_order(db, actor.user_id, body.notes,
                                      session_id=actor.session_id, guest_email=body.guest_email)
    audit_service.log(db, "order.place", actor_id=actor.user_id, target=order.order_number,
                      detail={"total_cents": order.total_cents, "guest": actor.is_guest},
                      ip=request.client.host if request.client else None)
    return order


@router.get("", response_model=list[OrderOut])
def my_orders(user=Depends(get_current_user), db=Depends(get_db)):
    # Order history is a logged-in feature; guests have no history.
    return order_service.list_orders(db, user.id)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, actor: Actor = Depends(get_actor), db=Depends(get_db)):
    order = order_service.get_order(db, order_id)
    if actor.owns(user_id=order.user_id, session_id=order.session_id):
        return order
    # admins may view any order
    if actor.user_id:
        from app.models.user import User
        u = db.get(User, actor.user_id)
        if u and u.role == "admin":
            return order
    raise NotFoundError()  # IDOR guard: 404, no existence leak
