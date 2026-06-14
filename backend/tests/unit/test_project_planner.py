"""Deterministic project-math tests (keyless, no DB)."""

from __future__ import annotations

import pytest

from app.ai.projects import PROJECT_TYPES, ProjectPlanError, plan_materials


def _by_role(plan: dict) -> dict:
    return {m["role"]: m for m in plan["materials"]}


def test_paint_room_quantities():
    plan = plan_materials("paint_room", {"length_ft": 12, "width_ft": 10, "height_ft": 8})
    roles = _by_role(plan)
    # perimeter 44, wall 352, paintable 316.8 → 2 coats / 350 = 2 gallons
    assert roles["paint"]["quantity"] == 2
    assert roles["primer"]["quantity"] == 1
    assert roles["tape"]["quantity"] == 1
    assert plan["derived"]["perimeter_ft"] == 44
    assert plan["derived"]["floor_area_sqft"] == 120


def test_paint_room_height_and_coats_defaults():
    plan = plan_materials("paint_room", {"length_ft": 12, "width_ft": 10})
    assert plan["dimensions"]["height_ft"] == 8.0  # default
    assert plan["dimensions"]["coats"] == 2         # default


def test_more_coats_increases_paint():
    one = plan_materials("paint_room", {"length_ft": 20, "width_ft": 20, "coats": 1})
    three = plan_materials("paint_room", {"length_ft": 20, "width_ft": 20, "coats": 3})
    assert _by_role(three)["paint"]["quantity"] > _by_role(one)["paint"]["quantity"]


def test_tile_floor_quantities():
    plan = plan_materials("tile_floor", {"length_ft": 10, "width_ft": 12})
    roles = _by_role(plan)
    assert roles["tile"]["quantity"] == 9     # 120*1.1/15 → ceil(8.8)
    assert roles["adhesive"]["quantity"] == 2  # 120/80 → ceil(1.5)
    assert roles["grout"]["quantity"] == 1


def test_laminate_floor_has_planks_and_underlayment():
    plan = plan_materials("laminate_floor", {"length_ft": 15, "width_ft": 15})
    roles = _by_role(plan)
    assert roles["plank"]["quantity"] >= 1
    assert roles["underlayment"]["quantity"] >= 1


def test_drywall_room_quantities():
    plan = plan_materials("drywall_room", {"length_ft": 12, "width_ft": 12, "height_ft": 8})
    roles = _by_role(plan)
    assert roles["drywall"]["quantity"] >= 1
    assert roles["screws"]["quantity"] >= 1


def test_quantities_scale_with_area():
    small = plan_materials("tile_floor", {"length_ft": 5, "width_ft": 5})
    big = plan_materials("tile_floor", {"length_ft": 20, "width_ft": 20})
    assert _by_role(big)["tile"]["quantity"] > _by_role(small)["tile"]["quantity"]


def test_unknown_project_type_raises():
    with pytest.raises(ProjectPlanError):
        plan_materials("build_spaceship", {"length_ft": 10, "width_ft": 10})


def test_missing_dimension_raises():
    with pytest.raises(ProjectPlanError):
        plan_materials("paint_room", {"width_ft": 10})


def test_out_of_range_dimension_raises():
    with pytest.raises(ProjectPlanError):
        plan_materials("paint_room", {"length_ft": 9999, "width_ft": 10})


def test_all_registered_types_plan_without_error():
    for ptype in PROJECT_TYPES:
        plan = plan_materials(ptype, {"length_ft": 10, "width_ft": 12, "height_ft": 8})
        assert plan["materials"], f"{ptype} produced no materials"
        for m in plan["materials"]:
            assert m["quantity"] >= 1
