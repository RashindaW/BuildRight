"""DB-backed tests for the project-planning tool executors (uses the seeded catalog)."""

from __future__ import annotations

import json

import pytest

from app.ai.context import ToolContext
from app.ai.guardrails import validate_response
from app.ai.tools import (
    execute_add_materials_to_cart,
    execute_compute_materials,
    execute_suggest_complementary,
)
from app.core.db import SessionLocal


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _ctx(db, **kw):
    return ToolContext(menu=[], db=db, **kw)


def test_compute_materials_resolves_real_skus_and_grounds_prices(db):
    js, grounded = execute_compute_materials(
        {"project_type": "paint_room", "length_ft": 12, "width_ft": 10, "height_ft": 8},
        _ctx(db),
    )
    out = json.loads(js)
    assert out["project_type"] == "paint_room"
    # At least the paint line resolved to a real catalog product with a SKU + price.
    resolved = [m for m in out["materials"] if m.get("sku")]
    assert resolved, "no materials resolved to a SKU"
    assert all("$" in m["unit_price"] for m in resolved)
    # Subtotal equals the sum of resolved line totals.
    line_sum = sum(float(m["line_total"].lstrip("$")) for m in resolved)
    assert abs(line_sum - float(out["subtotal"].lstrip("$"))) < 0.01
    # The subtotal is grounded, so the guardrail will accept the assistant quoting it.
    assert any(g["id"] == "project_subtotal" for g in grounded)


def test_compute_materials_subtotal_passes_price_guardrail(db):
    js, grounded = execute_compute_materials(
        {"project_type": "tile_floor", "length_ft": 10, "width_ft": 12}, _ctx(db)
    )
    out = json.loads(js)
    answer = f"Your project comes to {out['subtotal']} in total."
    result = validate_response(answer, grounded, allow_multiples=True)
    assert result.ok, result.reason


def test_compute_materials_invalid_type_returns_error(db):
    js, grounded = execute_compute_materials(
        {"project_type": "nope", "length_ft": 10, "width_ft": 10}, _ctx(db)
    )
    out = json.loads(js)
    assert out["error"] == "invalid_project"
    assert grounded is None
    assert "supported" in out


def test_add_materials_to_cart_guest_session(db):
    # Resolve a real SKU first.
    js, _ = execute_compute_materials(
        {"project_type": "paint_room", "length_ft": 10, "width_ft": 10}, _ctx(db)
    )
    mat = next(m for m in json.loads(js)["materials"] if m.get("sku"))

    ctx = _ctx(db, session_id="proj-test-session")
    add_js, payload = execute_add_materials_to_cart(
        {"items": [{"item": mat["sku"], "quantity": mat["quantity"]}]}, ctx
    )
    out = json.loads(add_js)
    assert payload["added"] is True
    assert out["added"] and out["added"][0]["sku"] == mat["sku"]
    assert out["added"][0]["quantity"] == mat["quantity"]


def test_add_materials_requires_actor(db):
    js, payload = execute_add_materials_to_cart(
        {"items": [{"item": "anything", "quantity": 1}]}, _ctx(db)  # no user, no session
    )
    assert json.loads(js)["error"] == "login_required"
    assert payload == {"added": False}


def test_suggest_complementary_returns_instock_items(db):
    js, grounded = execute_suggest_complementary({"project_type": "paint_room"}, _ctx(db))
    out = json.loads(js)
    assert out["suggestions"], "expected complementary suggestions"
    assert all("$" in s["price"] for s in out["suggestions"])
    assert len(grounded) == len(out["suggestions"])
