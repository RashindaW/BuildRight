"""Keyless tests for the search_menu tool executor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from menu_data import MENU_DATA  # noqa: E402

from app.ai.tools import execute_search_menu  # noqa: E402

# MENU_DATA items already carry allergens/dietary_tags.
MENU = [
    {**i, "allergens": i.get("allergens", [])} for i in MENU_DATA
]


def _names(js: str) -> set[str]:
    return {r["name"] for r in json.loads(js)["results"]}


def test_category_filter():
    js, items = execute_search_menu({"category": "pizza"}, MENU)
    assert _names(js) == {i["name"] for i in MENU if i["category"] == "pizza"}
    assert all(i["category"] == "pizza" for i in items)


def test_dietary_and_max_price():
    js, items = execute_search_menu({"dietary": ["vegan"], "max_price": 5.0}, MENU)
    for i in items:
        assert "vegan" in i["dietary_tags"] and i["price"] <= 5.0


def test_exclude_allergen():
    js, items = execute_search_menu({"exclude_allergen": ["tree-nuts"]}, MENU)
    assert all("tree-nuts" not in i.get("allergens", []) for i in items)


def test_query_keyword():
    js, items = execute_search_menu({"query": "caesar"}, MENU)
    assert any("Caesar" in n for n in _names(js))


def test_no_match_returns_note():
    js, items = execute_search_menu({"query": "sushi"}, MENU)
    data = json.loads(js)
    assert data["results"] == [] and "note" in data
    assert items == []


def test_prices_are_formatted():
    js, _ = execute_search_menu({"category": "drink"}, MENU)
    for r in json.loads(js)["results"]:
        assert r["price"].startswith("$") and r["price"].count(".") == 1
