from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.ai import service
from app.main import app


async def _fake_stream(prior, grounded, question, max_tokens=None):
    yield {"event": "start", "data": {}}
    yield {"event": "delta", "data": {"text": "The Classic Latte "}}
    yield {"event": "delta", "data": {"text": "is $4.50."}}
    yield {"event": "done", "data": {"text": "The Classic Latte is $4.50.",
                                      "input_tokens": 10, "output_tokens": 8,
                                      "guardrail_violation": False}}


def _auth_client():
    c = TestClient(app)
    email = f"chat-{uuid.uuid4().hex[:8]}@example.com"
    c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    c.headers.update({"x-csrf-token": c.cookies.get("csrf_token")})
    return c


def test_chat_stream_emits_sse_frames(monkeypatch):
    monkeypatch.setattr(service, "stream_chat", _fake_stream)
    c = _auth_client()
    r = c.post("/api/v1/chat/stream", json={"message": "how much is the latte?"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert "event: meta" in body
    assert "event: delta" in body
    assert "event: done" in body
    assert "$4.50" in body


def test_chat_requires_csrf():
    c = TestClient(app)
    email = f"chat2-{uuid.uuid4().hex[:8]}@example.com"
    c.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    # no CSRF header
    r = c.post("/api/v1/chat/stream", json={"message": "hi"})
    assert r.status_code == 403


def test_chat_message_length_limit():
    c = _auth_client()
    r = c.post("/api/v1/chat/stream", json={"message": "x" * 3000})
    assert r.status_code == 422  # schema max_length


def test_anonymous_chat_allowed(monkeypatch):
    monkeypatch.setattr(service, "stream_chat", _fake_stream)
    c = TestClient(app)
    # anonymous: need a CSRF token first
    csrf = c.get("/api/v1/auth/csrf").json()["csrf_token"]
    r = c.post("/api/v1/chat/stream",
               json={"message": "what's vegan?"},
               headers={"x-csrf-token": csrf, "x-session-id": "anon-123"})
    assert r.status_code == 200
    assert "event: done" in r.text
