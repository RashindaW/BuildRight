from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError
from app.models.cart import Cart, CartItem, CartItemOption
from app.models.menu import MenuItem, OptionChoice
from app.schemas.cart import CartItemOut, CartOut


def get_or_create_cart(db: Session, user_id: str | None = None, session_id: str | None = None) -> Cart:
    """Return the active cart for a logged-in user OR an anonymous guest session.

    A guest cart is keyed on session_id (with user_id NULL); a user cart on user_id.
    """
    if user_id:
        where = (Cart.user_id == user_id, Cart.status == "active")
    elif session_id:
        where = (Cart.session_id == session_id, Cart.user_id.is_(None), Cart.status == "active")
    else:
        raise AppError("No cart owner (user or session) provided", "no_cart_owner", 400)

    cart = db.execute(
        select(Cart).where(*where)
        .options(selectinload(Cart.items).selectinload(CartItem.menu_item))
    ).scalars().first()
    if cart is None:
        cart = Cart(user_id=user_id, session_id=None if user_id else session_id, status="active")
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


def add_item(db: Session, user_id: str | None, menu_item_id: str, quantity: int,
             option_choice_ids: list[str], session_id: str | None = None) -> Cart:
    cart = get_or_create_cart(db, user_id, session_id)
    item = _resolve_item(db, menu_item_id)

    cart_item = CartItem(cart_id=cart.id, menu_item_id=item.id, quantity=max(1, min(quantity, 99)))
    db.add(cart_item)
    db.flush()
    for choice_id in option_choice_ids:
        choice = db.get(OptionChoice, choice_id)
        if choice:
            db.add(CartItemOption(cart_item_id=cart_item.id, option_choice_id=choice.id))
    db.commit()
    return get_or_create_cart(db, user_id, session_id)


def mark_cart_source(db: Session, user_id: str | None, source: str,
                     conversation_id: str | None = None, session_id: str | None = None) -> Cart:
    """Tag the active cart with the channel that last touched it (for sales attribution).
    Called when a chat/voice tool adds items so the resulting order can be traced back
    to the AI conversation."""
    cart = get_or_create_cart(db, user_id, session_id)
    cart.source = source
    if conversation_id:
        cart.conversation_id = conversation_id
    db.commit()
    return cart


def update_quantity(db: Session, user_id: str | None, cart_item_id: str, quantity: int,
                    session_id: str | None = None) -> Cart:
    cart = get_or_create_cart(db, user_id, session_id)
    ci = db.get(CartItem, cart_item_id)
    if not ci or ci.cart_id != cart.id:
        raise NotFoundError("Cart item")
    if quantity <= 0:
        db.delete(ci)
    else:
        ci.quantity = min(quantity, 99)
    db.commit()
    return get_or_create_cart(db, user_id, session_id)


def remove_item(db: Session, user_id: str | None, cart_item_id: str,
                session_id: str | None = None) -> Cart:
    cart = get_or_create_cart(db, user_id, session_id)
    ci = db.get(CartItem, cart_item_id)
    if not ci or ci.cart_id != cart.id:
        raise NotFoundError("Cart item")
    db.delete(ci)
    db.commit()
    return get_or_create_cart(db, user_id, session_id)


def clear_cart(db: Session, user_id: str | None, session_id: str | None = None) -> Cart:
    cart = get_or_create_cart(db, user_id, session_id)
    for ci in list(cart.items):
        db.delete(ci)
    db.commit()
    return get_or_create_cart(db, user_id, session_id)


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
