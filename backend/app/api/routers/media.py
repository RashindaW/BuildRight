"""Multimodal endpoints: image product search + handwritten stock-sheet OCR.

- POST /media/find-by-image   (public)  — "find this item" from a photo
- POST /media/ocr-stock       (staff)   — OCR a count sheet → preview (no write)
- POST /media/stock/apply     (staff)   — apply confirmed counts (audited)

Vision calls need a real ANTHROPIC_API_KEY; failures degrade gracefully.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import vision
from app.core.db import get_db
from app.core.deps import require_staff
from app.core.errors import AppError
from app.models.menu import MenuItem
from app.schemas.menu import MenuItemOut
from app.services import audit_service

router = APIRouter(prefix="/media", tags=["media"])

_MAX_UPLOAD = vision.MAX_IMAGE_BYTES


async def _read_image(file: UploadFile) -> tuple[bytes, str]:
    data = await file.read()
    try:
        mt = vision.validate_image(data, file.content_type)
    except vision.VisionError as e:
        raise AppError(str(e), "invalid_image", 422)
    return data, mt


def _resolve_item(db: Session, raw: str) -> MenuItem | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    mi = db.execute(
        select(MenuItem).where(
            (func.lower(MenuItem.sku) == raw.lower())
            | (MenuItem.id == raw)
            | (MenuItem.slug == raw.lower())
        )
    ).scalar_one_or_none()
    if mi:
        return mi
    return db.execute(
        select(MenuItem).where(func.lower(MenuItem.name).contains(raw.lower()))
    ).scalars().first()


# ---- Find this item -------------------------------------------------------

@router.post("/find-by-image")
async def find_by_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Identify a product from a photo and return matching catalog items."""
    from app.ai.hybrid import hybrid_search_products

    data, mt = await _read_image(file)
    query = vision.describe_image_for_search(data, mt)
    if not query:
        return {"query": "", "results": [],
                "note": "Couldn't identify the item — try a clearer, closer photo."}

    items = hybrid_search_products(db, query, filters={"in_stock_only": True}, k=12)
    slugs = [it.get("slug") or it.get("id") for it in items]
    rows = db.execute(
        select(MenuItem).where(MenuItem.slug.in_(slugs))
    ).scalars().unique().all() if slugs else []
    by_slug = {r.slug: r for r in rows}
    results = [MenuItemOut.from_model(by_slug[s]) for s in slugs if s in by_slug]
    return {"query": query, "results": results}


# ---- Handwritten stock intake (staff) -------------------------------------

@router.post("/ocr-stock")
async def ocr_stock(file: UploadFile = File(...), db: Session = Depends(get_db),
                    user=Depends(require_staff)):
    """OCR a (handwritten) count sheet into a confirmable preview. No DB write."""
    data, mt = await _read_image(file)
    rows = vision.extract_stock_counts(data, mt)
    preview = []
    for r in rows:
        mi = _resolve_item(db, r["item"])
        preview.append({
            "item": r["item"],
            "qty": r["qty"],
            "matched": (
                {"menu_item_id": mi.id, "sku": mi.sku, "name": mi.name,
                 "current_stock": mi.stock_qty}
                if mi else None
            ),
        })
    return {
        "rows": preview,
        "matched_count": sum(1 for p in preview if p["matched"]),
        "note": "Review and confirm before applying. Unmatched rows are skipped.",
    }


class StockUpdate(BaseModel):
    menu_item_id: str
    qty: int = Field(ge=0, le=100000)


class StockApplyIn(BaseModel):
    updates: list[StockUpdate] = Field(min_length=1, max_length=500)


@router.post("/stock/apply")
def apply_stock(body: StockApplyIn, db: Session = Depends(get_db), user=Depends(require_staff)):
    """Apply confirmed stock counts (the human-confirm step). Each change audited."""
    updated = []
    for u in body.updates:
        mi = db.get(MenuItem, u.menu_item_id)
        if mi is None:
            continue
        old = mi.stock_qty
        mi.stock_qty = u.qty
        if u.qty > 0 and not mi.is_available:
            mi.is_available = True
        updated.append({"menu_item_id": mi.id, "sku": mi.sku, "name": mi.name,
                        "old_stock": old, "new_stock": mi.stock_qty})
        audit_service.log(
            db, "stock_intake_apply", actor_id=user.id, target=mi.id,
            detail={"old": old, "new": mi.stock_qty}, commit=False,
        )
    db.commit()
    return {"updated": updated, "count": len(updated)}
