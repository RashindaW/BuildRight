"""Customer-satisfaction (CSAT) feedback + manager summary."""

from __future__ import annotations

import pytest

from app.core.db import SessionLocal
from app.models.chat import Conversation


def _conversation_for(email_user_id: str) -> str:
    db = SessionLocal()
    try:
        conv = Conversation(user_id=email_user_id, title="csat-test")
        db.add(conv)
        db.commit()
        return conv.id
    finally:
        db.close()


def _me_id(client) -> str:
    return client.get("/api/v1/auth/me").json()["id"]


def test_feedback_persists_and_is_idempotent(customer_client):
    conv_id = _conversation_for(_me_id(customer_client))
    r = customer_client.post("/api/v1/chat/feedback",
                             json={"conversation_id": conv_id, "rating": 5, "comment": "great"})
    assert r.status_code == 200, r.text
    assert r.json()["rating"] == 5

    # Re-rating the same conversation updates (no duplicate row).
    r2 = customer_client.post("/api/v1/chat/feedback",
                              json={"conversation_id": conv_id, "rating": 3})
    assert r2.status_code == 200

    db = SessionLocal()
    try:
        from app.models.feedback import ConversationFeedback
        from sqlalchemy import select
        rows = db.execute(
            select(ConversationFeedback).where(ConversationFeedback.conversation_id == conv_id)
        ).scalars().all()
        assert len(rows) == 1 and rows[0].rating == 3
    finally:
        db.close()


def test_feedback_rejects_out_of_range(customer_client):
    conv_id = _conversation_for(_me_id(customer_client))
    r = customer_client.post("/api/v1/chat/feedback", json={"conversation_id": conv_id, "rating": 6})
    assert r.status_code == 422


def test_feedback_other_users_conversation_404(customer_client):
    # A guest conversation owned by a different session → not resolvable by this user.
    db = SessionLocal()
    try:
        conv = Conversation(user_id=None, session_id="someone-elses-session", title="x")
        db.add(conv)
        db.commit()
        other = conv.id
    finally:
        db.close()
    r = customer_client.post("/api/v1/chat/feedback", json={"conversation_id": other, "rating": 5})
    assert r.status_code == 404


def test_csat_summary_endpoint(admin_client, customer_client):
    conv_id = _conversation_for(_me_id(customer_client))
    customer_client.post("/api/v1/chat/feedback", json={"conversation_id": conv_id, "rating": 4})
    r = admin_client.get("/api/v1/analytics/csat?days=30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["responses"] >= 1
    assert 1.0 <= body["average"] <= 5.0
    assert set(body["histogram"]) == {"1", "2", "3", "4", "5"}


def test_csat_requires_manager(customer_client):
    assert customer_client.get("/api/v1/analytics/csat").status_code == 403
