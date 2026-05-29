from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import verify_csrf
from app.schemas.cart import CartItemIn, CartOut
from app.schemas.common import MessageResponse
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(user=Depends(get_current_user), db=Depends(get_db)):
    return cart_service.serialize_cart(cart_service.get_or_create_cart(db, user.id))


@router.post("/items", response_model=CartOut, dependencies=[Depends(verify_csrf)])
def add_item(body: CartItemIn, user=Depends(get_current_user), db=Depends(get_db)):
    cart = cart_service.add_item(db, user.id, body.menu_item_id, body.quantity, body.option_choice_ids)
    return cart_service.serialize_cart(cart)


@router.patch("/items/{cart_item_id}", response_model=CartOut, dependencies=[Depends(verify_csrf)])
def update_item(cart_item_id: str, quantity: int, user=Depends(get_current_user), db=Depends(get_db)):
    cart = cart_service.update_quantity(db, user.id, cart_item_id, quantity)
    return cart_service.serialize_cart(cart)


@router.delete("/items/{cart_item_id}", response_model=CartOut, dependencies=[Depends(verify_csrf)])
def remove_item(cart_item_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    cart = cart_service.remove_item(db, user.id, cart_item_id)
    return cart_service.serialize_cart(cart)


@router.delete("", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
def clear(user=Depends(get_current_user), db=Depends(get_db)):
    cart_service.clear_cart(db, user.id)
    return MessageResponse(message="cart cleared")
