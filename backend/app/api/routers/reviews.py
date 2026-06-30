"""Product reviews — public list + summary, authenticated/guest create (CSRF + moderated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Actor, get_actor
from app.core.errors import AppError, NotFoundError
from app.core.rate_limit import limiter
from app.core.security import verify_csrf
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.safety.moderation import screen_message
from app.schemas.common import Page
from app.schemas.menu import ReviewIn, ReviewOut
from app.services import review_service

router = APIRouter(prefix="/menu", tags=["reviews"])


def _item(db: Session, slug: str) -> MenuItem:
    item = db.execute(select(MenuItem).where(MenuItem.slug == slug)).scalar_one_or_none()
    if not item:
        raise NotFoundError("Menu item")
    return item


@router.get("/{slug}/reviews", response_model=Page[ReviewOut])
def list_reviews(
    slug: str,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
):
    item = _item(db, slug)
    rows = (
        db.execute(
            select(Review).where(Review.menu_item_id == item.id).order_by(Review.created_at.desc())
        )
        .scalars()
        .all()
    )
    start = (page - 1) * page_size
    return Page(
        items=[ReviewOut.model_validate(r) for r in rows[start : start + page_size]],
        total=len(rows),
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}/review-summary")
def review_summary(slug: str, db: Session = Depends(get_db)):
    item = _item(db, slug)
    return review_service.summarize(db, item.id)


@router.post("/{slug}/reviews", response_model=ReviewOut, dependencies=[Depends(verify_csrf)])
@limiter.limit("10/minute")
def create_review(
    slug: str,
    body: ReviewIn,
    request: Request,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
):
    item = _item(db, slug)

    if body.comment:
        allowed, _reason = screen_message(body.comment)
        if not allowed:
            raise AppError("Your review couldn't be posted.", "review_rejected", 400)

    # One review per logged-in user per product.
    if actor.user_id:
        existing = db.execute(
            select(Review.id).where(
                Review.menu_item_id == item.id, Review.user_id == actor.user_id
            )
        ).first()
        if existing:
            raise AppError("You've already reviewed this product.", "already_reviewed", 409)

    # Mark verified-purchase when the author has actually ordered this item.
    verified = False
    if actor.user_id:
        verified = (
            db.execute(
                select(OrderItem.id)
                .join(Order, Order.id == OrderItem.order_id)
                .where(Order.user_id == actor.user_id, OrderItem.menu_item_id == item.id)
                .limit(1)
            ).first()
            is not None
        )

    review = Review(
        menu_item_id=item.id,
        rating=body.rating,
        comment=(body.comment or None),
        author_name=(body.author_name or "Anonymous").strip()[:80] or "Anonymous",
        user_id=actor.user_id,
        session_id=actor.session_id,
        sentiment=review_service.sentiment_for(body.rating),
        verified_purchase=verified,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)
