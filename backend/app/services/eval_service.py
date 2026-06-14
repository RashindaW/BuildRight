"""Evaluate persisted chat turns offline and aggregate the scores.

Rehydrates each assistant message with the user question that preceded it and the
grounded item prices it cited (looked up from the catalog via the stored
grounded_item_ids), then scores it with the deterministic evaluator. Never runs
in the chat hot path.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.eval import evaluate_turn
from app.models.chat import Message
from app.models.menu import MenuItem

_METRICS = ("price_faithfulness", "answer_relevance", "context_utilization", "overall")


def _rehydrate_grounded(db: Session, item_ids: list[str] | None) -> list[dict]:
    ids = [i for i in (item_ids or []) if i]
    if not ids:
        return []
    rows = db.execute(
        select(MenuItem).where((MenuItem.slug.in_(ids)) | (MenuItem.id.in_(ids)))
    ).scalars().unique().all()
    return [{"id": r.slug, "name": r.name, "price": r.price_cents / 100} for r in rows]


def evaluate_recent(db: Session, limit: int = 50) -> dict:
    """Score the most recent assistant turns. Returns per-turn rows + aggregate means."""
    assistants = db.execute(
        select(Message)
        .where(Message.role == "assistant", Message.content != "")
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).scalars().all()

    rows = []
    for msg in assistants:
        question = _preceding_question(db, msg)
        grounded = _rehydrate_grounded(db, msg.grounded_item_ids)
        scores = evaluate_turn(question, msg.content, grounded)
        rows.append({
            "message_id": msg.id,
            "conversation_id": msg.conversation_id,
            "grounded_item_count": len(grounded),
            **scores,
        })

    aggregate = {m: round(sum(r[m] for r in rows) / len(rows), 4) for m in _METRICS} if rows else {
        m: None for m in _METRICS
    }
    return {"evaluated": len(rows), "aggregate": aggregate, "rows": rows}


def _preceding_question(db: Session, assistant_msg: Message) -> str:
    """The most recent user message before this assistant turn in the same conversation."""
    prev = db.execute(
        select(Message)
        .where(
            Message.conversation_id == assistant_msg.conversation_id,
            Message.role == "user",
            Message.created_at <= assistant_msg.created_at,
            Message.id != assistant_msg.id,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    ).scalars().first()
    return prev.content if prev else ""


def overall_health(db: Session) -> dict:
    """Lightweight totals for the dashboard header."""
    total = db.execute(
        select(func.count(Message.id)).where(Message.role == "assistant")
    ).scalar() or 0
    return {"assistant_turns": int(total)}
