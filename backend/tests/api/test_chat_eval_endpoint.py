"""Chat-eval service + admin endpoint (DB-backed)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.chat import Conversation, Message
from app.models.menu import MenuItem
from app.services import eval_service


@pytest.fixture
def seeded_conversation():
    """A conversation with one user question + one grounded assistant answer."""
    db = SessionLocal()
    try:
        item = db.execute(
            select(MenuItem).where(MenuItem.is_available.is_(True))
        ).scalars().first()
        price = item.price_cents / 100
        conv = Conversation(title="eval-test")
        db.add(conv)
        db.flush()
        db.add(Message(conversation_id=conv.id, role="user",
                       content=f"how much is the {item.name}"))
        db.flush()
        db.add(Message(
            conversation_id=conv.id, role="assistant",
            content=f"The {item.name} is ${price:.2f}.",
            grounded_item_ids=[item.slug],
        ))
        db.commit()
        return {"conversation_id": conv.id, "item": item.name, "price": price}
    finally:
        db.close()


def test_evaluate_recent_scores_grounded_turn(seeded_conversation):
    db = SessionLocal()
    try:
        report = eval_service.evaluate_recent(db, limit=100)
        assert report["evaluated"] >= 1
        row = next(r for r in report["rows"]
                   if r["conversation_id"] == seeded_conversation["conversation_id"])
        assert row["price_faithfulness"] == 1.0       # the stated price is grounded
        assert row["context_utilization"] == 1.0      # the product was named
        assert row["grounded_item_count"] == 1
    finally:
        db.close()


def test_chat_eval_endpoint_requires_manager(customer_client):
    r = customer_client.get("/api/v1/analytics/chat-eval")
    assert r.status_code == 403


def test_chat_eval_endpoint_returns_aggregate(admin_client, seeded_conversation):
    r = admin_client.get("/api/v1/analytics/chat-eval?limit=100")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["evaluated"] >= 1
    assert set(body["aggregate"]) == {
        "price_faithfulness", "answer_relevance", "context_utilization", "overall",
    }
    assert 0.0 <= body["aggregate"]["overall"] <= 1.0
