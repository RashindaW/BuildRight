from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.menu import Allergen, Category, DietaryTag, MenuItem
from app.schemas.common import Page
from app.schemas.menu import CategoryOut, MenuItemOut

router = APIRouter(prefix="/menu", tags=["menu"])


def _base_query():
    return select(MenuItem).options(
        selectinload(MenuItem.category),
        selectinload(MenuItem.dietary_tags),
        selectinload(MenuItem.allergens),
        selectinload(MenuItem.option_groups),
    )


@router.get("", response_model=Page[MenuItemOut])
def list_menu(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=100),
    category: str | None = None,
    dietary: list[str] | None = Query(default=None),
    exclude_allergen: list[str] | None = Query(default=None),
    available_only: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    stmt = _base_query()
    if available_only:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    if category:
        stmt = stmt.join(MenuItem.category).where(Category.slug == category)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(MenuItem.name).like(like)
            | func.lower(MenuItem.description).like(like)
            | func.lower(MenuItem.sku).like(like)
        )
    if dietary:
        for tag in dietary:
            stmt = stmt.where(MenuItem.dietary_tags.any(DietaryTag.slug == tag))
    if exclude_allergen:
        for a in exclude_allergen:
            stmt = stmt.where(~MenuItem.allergens.any(Allergen.slug == a))

    all_items = db.execute(stmt).scalars().unique().all()
    total = len(all_items)
    start = (page - 1) * page_size
    page_items = all_items[start:start + page_size]
    return Page(
        items=[MenuItemOut.from_model(i) for i in page_items],
        total=total, page=page, page_size=page_size,
    )


class ItemsByIds(BaseModel):
    ids: list[str] = Field(default_factory=list)


@router.post("/by-ids", response_model=list[MenuItemOut])
def items_by_ids(body: ItemsByIds, db: Session = Depends(get_db)):
    """Hydrate a list of product slugs/ids (e.g. the chat's grounded_item_ids) into full
    items, preserving the requested order. Used to render chat-shortlisted products."""
    ids = [i for i in body.ids if i][:100]
    if not ids:
        return []
    items = db.execute(
        _base_query().where((MenuItem.slug.in_(ids)) | (MenuItem.id.in_(ids)))
    ).scalars().unique().all()
    by_key: dict[str, MenuItem] = {}
    for it in items:
        by_key.setdefault(it.slug, it)
        by_key.setdefault(it.id, it)
    out, seen = [], set()
    for k in ids:
        it = by_key.get(k)
        if it and it.id not in seen:
            seen.add(it.id)
            out.append(MenuItemOut.from_model(it))
    return out


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    cats = db.execute(select(Category).order_by(Category.display_order, Category.name)).scalars().all()
    return [CategoryOut.model_validate(c) for c in cats]


@router.get("/{slug}/recommendations", response_model=list[MenuItemOut])
def item_recommendations(slug: str, db: Session = Depends(get_db), limit: int = Query(6, ge=1, le=12)):
    """Product-page recommendations: real co-purchases first (collaborative
    filtering), topped up with content-similar items. Order-preserving + deduped."""
    from app.services.recommender_service import frequently_bought_with, recommend_similar

    ranked = frequently_bought_with(db, slug, k=limit) + recommend_similar(db, slug, k=limit)
    ids, seen = [], set()
    for r in ranked:
        if r["slug"] not in seen:
            seen.add(r["slug"])
            ids.append(r["slug"])
    ids = ids[:limit]
    if not ids:
        return []
    items = db.execute(_base_query().where(MenuItem.slug.in_(ids))).scalars().unique().all()
    by_slug = {it.slug: it for it in items}
    return [MenuItemOut.from_model(by_slug[s]) for s in ids if s in by_slug]


@router.get("/{slug}", response_model=MenuItemOut)
def get_item(slug: str, db: Session = Depends(get_db)):
    item = db.execute(_base_query().where(MenuItem.slug == slug)).scalars().first()
    if not item:
        raise NotFoundError("Menu item")
    return MenuItemOut.from_model(item)
