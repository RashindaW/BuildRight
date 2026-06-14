from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import require_admin
from app.core.errors import AppError, NotFoundError
from app.core.security import verify_csrf
from app.models.menu import Allergen, Category, DietaryTag, MenuItem
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.common import MessageResponse
from app.schemas.menu import MenuItemCreate, MenuItemOut, MenuItemUpdate
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.services import audit_service, order_service

router = APIRouter(
    prefix="/admin", tags=["admin"],
    dependencies=[Depends(require_admin), Depends(verify_csrf)],
)


def _apply_tags(db: Session, item: MenuItem, dietary: list[str] | None, allergens: list[str] | None):
    if dietary is not None:
        item.dietary_tags = db.execute(
            select(DietaryTag).where(DietaryTag.slug.in_(dietary))
        ).scalars().all()
    if allergens is not None:
        item.allergens = db.execute(
            select(Allergen).where(Allergen.slug.in_(allergens))
        ).scalars().all()


def _get_full(db: Session, item_id: str) -> MenuItem:
    item = db.execute(
        select(MenuItem).where(MenuItem.id == item_id).options(
            selectinload(MenuItem.category), selectinload(MenuItem.dietary_tags),
            selectinload(MenuItem.allergens), selectinload(MenuItem.option_groups),
        )
    ).scalars().first()
    if not item:
        raise NotFoundError("Menu item")
    return item


# ---- Menu CRUD ----------------------------------------------------------

@router.post("/menu", response_model=MenuItemOut, status_code=201)
def create_item(body: MenuItemCreate, request: Request, admin=Depends(require_admin),
                db: Session = Depends(get_db)):
    cat = db.execute(select(Category).where(Category.slug == body.category)).scalar_one_or_none()
    if not cat:
        raise AppError(f"Unknown category '{body.category}'", "bad_category", 400)
    if db.execute(select(MenuItem).where(MenuItem.slug == body.slug)).scalar_one_or_none():
        raise AppError("Slug already exists", "slug_taken", 409)
    item = MenuItem(
        slug=body.slug, name=body.name, description=body.description,
        price_cents=body.price_cents, cost_cents=body.cost_cents, category_id=cat.id,
        keywords=body.keywords, calories=body.calories, spice_level=body.spice_level,
        prep_time_min=body.prep_time_min, is_available=body.is_available,
        featured=body.featured, image_url=body.image_url,
    )
    db.add(item)
    db.flush()
    _apply_tags(db, item, body.dietary_tags, body.allergens)
    db.commit()
    audit_service.log(db, "admin.menu.create", actor_id=admin.id, target=body.slug)
    return MenuItemOut.from_model(_get_full(db, item.id))


@router.patch("/menu/{item_id}", response_model=MenuItemOut)
def update_item(item_id: str, body: MenuItemUpdate, admin=Depends(require_admin),
                db: Session = Depends(get_db)):
    item = _get_full(db, item_id)
    data = body.model_dump(exclude_unset=True)
    if "category" in data:
        cat = db.execute(select(Category).where(Category.slug == data["category"])).scalar_one_or_none()
        if not cat:
            raise AppError(f"Unknown category '{data['category']}'", "bad_category", 400)
        item.category_id = cat.id
    for f in ("name", "description", "price_cents", "cost_cents", "keywords", "calories",
              "spice_level", "prep_time_min", "is_available", "featured", "image_url"):
        if f in data:
            setattr(item, f, data[f])
    _apply_tags(db, item, data.get("dietary_tags"), data.get("allergens"))
    db.commit()
    audit_service.log(db, "admin.menu.update", actor_id=admin.id, target=item.slug, detail=data)
    return MenuItemOut.from_model(_get_full(db, item.id))


@router.delete("/menu/{item_id}", response_model=MessageResponse)
def delete_item(item_id: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if not item:
        raise NotFoundError("Menu item")
    slug = item.slug
    db.delete(item)
    db.commit()
    audit_service.log(db, "admin.menu.delete", actor_id=admin.id, target=slug)
    return MessageResponse(message=f"deleted {slug}")


# ---- Orders -------------------------------------------------------------

@router.get("/orders", response_model=list[OrderOut])
def all_orders(db: Session = Depends(get_db)):
    return db.execute(
        select(Order).order_by(Order.created_at.desc())
        .options(selectinload(Order.items).selectinload(OrderItem.options))
    ).scalars().all()


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def set_order_status(order_id: str, body: OrderStatusUpdate, admin=Depends(require_admin),
                     db: Session = Depends(get_db)):
    order = order_service.update_status(db, order_id, body.status)
    audit_service.log(db, "admin.order.status", actor_id=admin.id, target=order.order_number,
                      detail={"status": body.status})
    return order


# ---- Users --------------------------------------------------------------

@router.get("/users", response_model=list[UserOut])
def all_users(db: Session = Depends(get_db)):
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [UserOut.model_validate(u) for u in users]
