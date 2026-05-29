from __future__ import annotations

from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    model_config = {"extra": "forbid"}
    menu_item_id: str  # slug or id
    quantity: int = Field(default=1, ge=1, le=99)
    option_choice_ids: list[str] = []


class CartItemOut(BaseModel):
    id: str
    menu_item_id: str
    name: str
    slug: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    options: list[str] = []


class CartOut(BaseModel):
    id: str
    items: list[CartItemOut]
    subtotal_cents: int
    item_count: int
