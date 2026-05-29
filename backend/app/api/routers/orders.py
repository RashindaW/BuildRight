from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.db import get_db
from app.core.deps import get_current_user, get_owned_or_404
from app.core.security import verify_csrf
from app.schemas.order import OrderCreateIn, OrderOut
from app.services import audit_service, order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, dependencies=[Depends(verify_csrf)])
def create_order(body: OrderCreateIn, request: Request,
                 user=Depends(get_current_user), db=Depends(get_db)):
    order = order_service.place_order(db, user.id, body.notes)
    audit_service.log(db, "order.place", actor_id=user.id, target=order.order_number,
                      detail={"total_cents": order.total_cents},
                      ip=request.client.host if request.client else None)
    return order


@router.get("", response_model=list[OrderOut])
def my_orders(user=Depends(get_current_user), db=Depends(get_db)):
    return order_service.list_orders(db, user.id)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    order = order_service.get_order(db, order_id)
    get_owned_or_404(order.user_id, user)  # IDOR guard: 404 if not owner/admin
    return order
