from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import Actor, get_actor
from app.core.security import verify_csrf
from app.schemas.cart import CartItemIn, CartOut
from app.schemas.common import MessageResponse
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(actor: Actor = Depends(get_actor), db=Depends(get_db)):
    cart = cart_service.get_or_create_cart(db, actor.user_id, actor.session_id)
    return cart_service.serialize_cart(cart)


@router.post("/items", response_model=CartOut, dependencies=[Depends(verify_csrf)])
def add_item(body: CartItemIn, actor: Actor = Depends(get_actor), db=Depends(get_db)):
    cart = cart_service.add_item(db, actor.user_id, body.menu_item_id, body.quantity,
                                 body.option_choice_ids, session_id=actor.session_id)
    return cart_service.serialize_cart(cart)


@router.patch("/items/{cart_item_id}", response_model=CartOut, dependencies=[Depends(verify_csrf)])
def update_item(cart_item_id: str, quantity: int, actor: Actor = Depends(get_actor), db=Depends(get_db)):
    cart = cart_service.update_quantity(db, actor.user_id, cart_item_id, quantity,
                                        session_id=actor.session_id)
    return cart_service.serialize_cart(cart)


@router.delete("/items/{cart_item_id}", response_model=CartOut, dependencies=[Depends(verify_csrf)])
def remove_item(cart_item_id: str, actor: Actor = Depends(get_actor), db=Depends(get_db)):
    cart = cart_service.remove_item(db, actor.user_id, cart_item_id, session_id=actor.session_id)
    return cart_service.serialize_cart(cart)


@router.delete("", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
def clear(actor: Actor = Depends(get_actor), db=Depends(get_db)):
    cart_service.clear_cart(db, actor.user_id, session_id=actor.session_id)
    return MessageResponse(message="cart cleared")
