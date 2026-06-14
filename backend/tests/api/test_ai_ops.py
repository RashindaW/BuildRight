"""AI Operations aggregation + endpoint (DB-backed)."""

from __future__ import annotations

import pytest

from app.core.db import SessionLocal
from app.models.chat import Conversation, Message
from app.services import analytics_service


@pytest.fixture
def telemetry_turns():
    """Two assistant turns: a Haiku/simple one and a Sonnet/complex one (with tools)."""
    db = SessionLocal()
    try:
        conv = Conversation(title="aiops-test")
        db.add(conv)
        db.flush()
        db.add(Message(
            conversation_id=conv.id, role="assistant", content="cheap turn",
            model="claude-haiku-4-5", route="simple",
            input_tokens=1000, output_tokens=500,
            tools_used=["search_products"], guardrail_violation=False,
        ))
        db.add(Message(
            conversation_id=conv.id, role="assistant", content="planner turn",
            model="claude-sonnet-4-6", route="complex",
            input_tokens=2000, output_tokens=1000,
            tools_used=["compute_materials", "add_materials_to_cart"], guardrail_violation=True,
        ))
        db.commit()
        return conv.id
    finally:
        db.close()


def test_ai_operations_aggregates(telemetry_turns):
    db = SessionLocal()
    try:
        out = analytics_service.ai_operations(db, days=30, recent_limit=50)
        assert out["turns"] >= 2
        assert out["total_cost_usd"] > 0           # haiku + sonnet both priced
        # both models present in the cost table
        models = {r["model"] for r in out["by_model"]}
        assert {"claude-haiku-4-5", "claude-sonnet-4-6"} <= models
        # tool usage counted
        tools = {t["tool"]: t["count"] for t in out["tool_usage"]}
        assert tools.get("compute_materials", 0) >= 1
        assert tools.get("search_products", 0) >= 1
        # route mix has both simple and complex
        routes = {r["route"] for r in out["route_distribution"]}
        assert {"simple", "complex"} <= routes
        assert out["guardrail_violations"] >= 1
    finally:
        db.close()


def test_ai_ops_endpoint_requires_manager(customer_client):
    r = customer_client.get("/api/v1/analytics/ai-ops")
    assert r.status_code == 403


def test_ai_ops_endpoint_ok_for_manager(admin_client, telemetry_turns):
    r = admin_client.get("/api/v1/analytics/ai-ops?days=30")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(["turns", "total_cost_usd", "by_model", "route_distribution",
                "tool_usage", "recent", "quality"]) <= set(body)
    assert body["total_cost_usd"] >= 0
