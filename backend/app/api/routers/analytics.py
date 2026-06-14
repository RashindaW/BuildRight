"""Manager analytics endpoints (manager + admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_manager
from app.services import analytics_service, eval_service

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


@router.get("/chat-eval")
def chat_eval(limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    """Offline chat-quality scores (faithfulness / relevance / context use) over
    recent assistant turns, plus an aggregate. Deterministic; never blocks chat."""
    return eval_service.evaluate_recent(db, limit)
