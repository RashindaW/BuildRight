"""Adapter: DB MenuItem rows -> the exact PoC dict shape retrieval expects.

Price is reconstructed from integer cents as a float so that
`f"${price:.2f}"` is byte-identical to the PoC strings ($4.50, $11.50, ...).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.menu import MenuItem


def item_to_dict(item: MenuItem) -> dict:
    keywords = list(item.keywords or [])
    # Fold the SKU (and a hyphen-free alias) into keywords so the lexical retrieval
    # arm matches SKU lookups like "BR-PWR-04821" or "brpwr04821".
    if item.sku:
        keywords = keywords + [item.sku.lower(), item.sku.lower().replace("-", "")]
    return {
        "id": item.slug,
        "sku": item.sku,
        "name": item.name,
        "category": item.category.slug,
        "description": item.description,
        "price": item.price_cents / 100,
        "stock_qty": item.stock_qty,
        "is_available": item.is_available,
        "dietary_tags": sorted(t.slug for t in item.dietary_tags),
        "allergens": sorted(a.slug for a in item.allergens),
        "keywords": keywords,
    }


def get_menu_for_assistant(db: Session, available_only: bool = True) -> list[dict]:
    stmt = select(MenuItem).options(
        selectinload(MenuItem.category),
        selectinload(MenuItem.dietary_tags),
        selectinload(MenuItem.allergens),
    )
    if available_only:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    items = db.execute(stmt).scalars().all()
    return [item_to_dict(i) for i in items]
