"""MCP boundary: tool exposure, RBAC, and read-only dispatch (DB-backed)."""

from __future__ import annotations

import json

import pytest

from app.core.db import SessionLocal
from app.mcp import MCP_TOOLS, McpAccessError, dispatch, list_tools


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def test_only_readonly_tools_are_exposed():
    exposed = set(MCP_TOOLS)
    # No mutation / user-scoped tools cross the boundary.
    for forbidden in ("reorder", "add_materials_to_cart", "set_preference", "get_order_history"):
        assert forbidden not in exposed
    assert "search_products" in exposed


def test_list_tools_descriptors():
    tools = list_tools()
    assert {t["name"] for t in tools} == set(MCP_TOOLS)
    assert all(t["description"] and t["input_schema"] for t in tools)


def test_dispatch_search_products(db):
    out = json.loads(dispatch("search_products", {"query": "cordless drill"}, db))
    assert "results" in out


def test_dispatch_unknown_tool_raises(db):
    with pytest.raises(McpAccessError):
        dispatch("delete_everything", {}, db)


def test_dispatch_rejects_insufficient_role(db):
    # 'guest' ranks below the customer minimum → blocked at the boundary.
    with pytest.raises(McpAccessError):
        dispatch("search_products", {"query": "x"}, db, role="guest")


def test_dispatch_recommend_similar(db):
    from sqlalchemy import select
    from app.models.menu import MenuItem
    slug = db.execute(select(MenuItem.slug)).scalars().first()
    out = json.loads(dispatch("recommend_similar", {"item": slug}, db))
    assert "recommendations" in out or "note" in out
