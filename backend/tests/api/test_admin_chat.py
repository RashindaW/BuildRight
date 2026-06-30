"""Admin 'ask your data' chat: RBAC gating, SSE wiring, and the analytics tool executors."""

from __future__ import annotations

import json

from app.ai.admin_tools import ADMIN_EXECUTORS
from app.core.db import SessionLocal


def test_admin_chat_requires_manager(customer_client):
    r = customer_client.post("/api/v1/admin/chat/stream", json={"message": "What were my margins?"})
    assert r.status_code == 403


def test_admin_chat_manager_streams(admin_client):
    r = admin_client.post("/api/v1/admin/chat/stream", json={"message": "How is inventory looking?"})
    assert r.status_code == 200
    assert "event: meta" in r.text  # the SSE stream started for an authorized manager


def test_admin_analytics_tools_execute():
    db = SessionLocal()

    class _Ctx:
        pass

    ctx = _Ctx()
    ctx.db = db
    try:
        out, payload = ADMIN_EXECUTORS["get_inventory"]({}, ctx)
        assert payload is None
        assert "total_products" in json.loads(out)

        margins, _ = ADMIN_EXECUTORS["get_margins"]({"days": 30}, ctx)
        assert "overall" in json.loads(margins)

        ops, _ = ADMIN_EXECUTORS["get_ai_ops"]({"days": 7}, ctx)
        assert "turns" in json.loads(ops)
    finally:
        db.close()
