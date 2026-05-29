from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OrderItemOptionOut(BaseModel):
    name_snapshot: str
    price_delta_cents: int


class OrderItemOut(BaseModel):
    id: str
    name_snapshot: str
    unit_price_cents: int
    quantity: int
    line_total_cents: int
    options: list[OrderItemOptionOut] = []


class OrderOut(BaseModel):
    id: str
    order_number: str
    status: str
    subtotal_cents: int
    total_cents: int
    notes: str | None
    created_at: datetime
    items: list[OrderItemOut]


class OrderCreateIn(BaseModel):
    model_config = {"extra": "forbid"}
    notes: str | None = Field(default=None, max_length=500)


class OrderStatusUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    status: str
