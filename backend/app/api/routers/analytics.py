"""Manager analytics endpoints (manager + admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_manager
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_manager)])


@router.get("/inventory")
def inventory(db: Session = Depends(get_db)):
    return analytics_service.inventory_summary(db)


@router.get("/margins")
def margins(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return analytics_service.margin_summary(db, days)


@router.get("/ai-attribution")
def ai_attribution(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return analytics_service.ai_attribution(db, days)
