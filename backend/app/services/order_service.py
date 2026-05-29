from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError
from app.models.order import ORDER_STATUSES, Order, OrderItem, OrderItemOption
from app.services import cart_service


def _generate_order_number() -> str:
    # UUID-based suffix avoids count()+1 races; human-readable prefix.
    return f"CD-{uuid.uuid4().hex[:10].upper()}"


def place_order(db: Session, user_id: str, notes: str | None = None) -> Order:
    cart = cart_service.get_or_create_cart(db, user_id)
    if not cart.items:
        raise AppError("Cart is empty", "empty_cart", 400)

    subtotal = 0
    order = Order(
        order_number=_generate_order_number(),
        user_id=user_id,
        status="placed",
        subtotal_cents=0,
        total_cents=0,
        notes=notes,
    )
    db.add(order)
    db.flush()

    for ci in cart.items:
        unit = cart_service._line_unit_cents(ci)
        line = unit * ci.quantity
        subtotal += line
        oi = OrderItem(
            order_id=order.id,
            menu_item_id=ci.menu_item.id,
            name_snapshot=ci.menu_item.name,
            unit_price_cents=unit,
            quantity=ci.quantity,
            line_total_cents=line,
        )
        db.add(oi)
        db.flush()
        for o in ci.options:
            db.add(OrderItemOption(
                order_item_id=oi.id,
                name_snapshot=o.option_choice.name,
                price_delta_cents=o.option_choice.price_delta_cents,
            ))

    order.subtotal_cents = subtotal
    order.total_cents = subtotal  # mock: no tax/fees
    cart.status = "converted"
    db.commit()
    db.refresh(order)
    return order


def list_orders(db: Session, user_id: str) -> list[Order]:
    return db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .options(selectinload(Order.items).selectinload(OrderItem.options))
    ).scalars().all()


def get_order(db: Session, order_id: str) -> Order:
    order = db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.options))
    ).scalars().first()
    if not order:
        raise NotFoundError("Order")
    return order


def update_status(db: Session, order_id: str, status: str) -> Order:
    if status not in ORDER_STATUSES:
        raise AppError(f"Invalid status. Must be one of {ORDER_STATUSES}", "invalid_status", 400)
    order = get_order(db, order_id)
    order.status = status
    db.commit()
    db.refresh(order)
    return order
