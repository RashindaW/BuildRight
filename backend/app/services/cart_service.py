from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError
from app.models.cart import Cart, CartItem, CartItemOption
from app.models.menu import MenuItem, OptionChoice
from app.schemas.cart import CartItemOut, CartOut


def get_or_create_cart(db: Session, user_id: str) -> Cart:
    cart = db.execute(
        select(Cart)
        .where(Cart.user_id == user_id, Cart.status == "active")
        .options(selectinload(Cart.items).selectinload(CartItem.menu_item))
    ).scalars().first()
    if cart is None:
        cart = Cart(user_id=user_id, status="active")
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _resolve_item(db: Session, menu_item_id: str) -> MenuItem:
    item = db.execute(
        select(MenuItem).where((MenuItem.id == menu_item_id) | (MenuItem.slug == menu_item_id))
    ).scalars().first()
    if not item:
        raise NotFoundError("Menu item")
    if not item.is_available:
        raise AppError("Item is not available", "unavailable", 409)
    return item


def add_item(db: Session, user_id: str, menu_item_id: str, quantity: int,
             option_choice_ids: list[str]) -> Cart:
    cart = get_or_create_cart(db, user_id)
    item = _resolve_item(db, menu_item_id)

    cart_item = CartItem(cart_id=cart.id, menu_item_id=item.id, quantity=quantity)
    db.add(cart_item)
    db.flush()
    for choice_id in option_choice_ids:
        choice = db.get(OptionChoice, choice_id)
        if choice:
            db.add(CartItemOption(cart_item_id=cart_item.id, option_choice_id=choice.id))
    db.commit()
    return get_or_create_cart(db, user_id)


def update_quantity(db: Session, user_id: str, cart_item_id: str, quantity: int) -> Cart:
    cart = get_or_create_cart(db, user_id)
    ci = db.get(CartItem, cart_item_id)
    if not ci or ci.cart_id != cart.id:
        raise NotFoundError("Cart item")
    if quantity <= 0:
        db.delete(ci)
    else:
        ci.quantity = quantity
    db.commit()
    return get_or_create_cart(db, user_id)


def remove_item(db: Session, user_id: str, cart_item_id: str) -> Cart:
    cart = get_or_create_cart(db, user_id)
    ci = db.get(CartItem, cart_item_id)
    if not ci or ci.cart_id != cart.id:
        raise NotFoundError("Cart item")
    db.delete(ci)
    db.commit()
    return get_or_create_cart(db, user_id)


def clear_cart(db: Session, user_id: str) -> Cart:
    cart = get_or_create_cart(db, user_id)
    for ci in list(cart.items):
        db.delete(ci)
    db.commit()
    return get_or_create_cart(db, user_id)


def _line_unit_cents(ci: CartItem) -> int:
    base = ci.menu_item.price_cents
    deltas = sum(o.option_choice.price_delta_cents for o in ci.options)
    return base + deltas


def serialize_cart(cart: Cart) -> CartOut:
    items_out = []
    subtotal = 0
    count = 0
    for ci in cart.items:
        unit = _line_unit_cents(ci)
        line = unit * ci.quantity
        subtotal += line
        count += ci.quantity
        items_out.append(CartItemOut(
            id=ci.id,
            menu_item_id=ci.menu_item.id,
            name=ci.menu_item.name,
            slug=ci.menu_item.slug,
            quantity=ci.quantity,
            unit_price_cents=unit,
            line_total_cents=line,
            options=[o.option_choice.name for o in ci.options],
        ))
    return CartOut(id=cart.id, items=items_out, subtotal_cents=subtotal, item_count=count)
