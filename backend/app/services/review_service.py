"""Product reviews: sentiment derivation, rating aggregates, and a review summary.

The summary is best-effort: it returns a deterministic rule-based sentence everywhere
(so tests stay keyless), and upgrades to a one-line LLM summary of the comments when a
real Anthropic key is configured (i.e. not in the test environment).
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.review import Review

logger = logging.getLogger("app.services.review_service")


def sentiment_for(rating: int) -> str:
    """Map a 1-5 rating to a coarse sentiment label."""
    if rating >= 4:
        return "positive"
    if rating <= 2:
        return "negative"
    return "neutral"


def rating_map(db: Session, item_ids: list[str]) -> dict[str, tuple[float, int]]:
    """{menu_item_id: (avg_rating, count)} for the given items (one grouped query)."""
    ids = [i for i in item_ids if i]
    if not ids:
        return {}
    rows = db.execute(
        select(Review.menu_item_id, func.avg(Review.rating), func.count(Review.id))
        .where(Review.menu_item_id.in_(ids))
        .group_by(Review.menu_item_id)
    ).all()
    return {mid: (round(float(avg), 2), int(cnt)) for mid, avg, cnt in rows}


def summarize(db: Session, item_id: str) -> dict:
    """A short 'what customers say' summary for a product's reviews."""
    rows = (
        db.execute(
            select(Review).where(Review.menu_item_id == item_id).order_by(Review.created_at.desc())
        )
        .scalars()
        .all()
    )
    n = len(rows)
    if n == 0:
        return {"count": 0, "average": None, "positive": 0, "negative": 0, "summary": ""}

    pos = sum(1 for r in rows if r.sentiment == "positive")
    neg = sum(1 for r in rows if r.sentiment == "negative")
    avg = round(sum(r.rating for r in rows) / n, 2)
    lean = "mostly positive" if pos >= neg else "mixed" if pos else "mostly critical"
    summary = f"Customers are {lean} ({pos} of {n} reviews positive, avg {avg}/5)."

    # Best-effort LLM upgrade over the actual comment text.
    commented = [rw for rw in rows if rw.comment and rw.comment.strip()][:25]
    if commented and settings.environment != "test" and settings.anthropic_api_key.get_secret_value():
        try:
            from app.ai.service import _get_sync_client

            joined = "\n".join(f"- ({rw.rating}/5) {rw.comment.strip()}" for rw in commented)
            resp = _get_sync_client().messages.create(
                model=settings.llm_model,
                max_tokens=80,
                temperature=0.0,
                system=(
                    "You summarize product reviews in ONE neutral sentence (max 30 words), "
                    "noting the main praise and the main complaint if present. No preamble."
                ),
                messages=[{"role": "user", "content": f"Reviews:\n{joined}"}],
            )
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            if text:
                summary = text
        except Exception as e:  # noqa: BLE001 - never block the page on a summary
            logger.info("review summary llm failed (%s); using rule-based", type(e).__name__)

    return {"count": n, "average": avg, "positive": pos, "negative": neg, "summary": summary}
