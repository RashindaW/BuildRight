"""GR tier — keyless retrieval-golden tests.

Proves the retrieval pipeline behaves identically to the PoC, with NO API key.
These run in milliseconds on every push and catch data/category/scoring
regressions before they reach the live LLM.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root for menu_data
from menu_data import MENU_DATA  # noqa: E402

from app.ai.retrieval import retrieve_relevant_items  # noqa: E402


def names(items):
    return {i["name"] for i in items}


def test_caesar_lookup():
    items = retrieve_relevant_items("do you have a caesar salad?", MENU_DATA)
    assert "Classic Caesar Salad" in names(items)


def test_vegan_returns_all_vegan_items():
    items = retrieve_relevant_items("what's vegan?", MENU_DATA)
    expected = {i["name"] for i in MENU_DATA if "vegan" in i["dietary_tags"]}
    assert names(items) == expected
    assert len(expected) >= 3


def test_generic_browse_returns_full_menu():
    items = retrieve_relevant_items("what's on the menu?", MENU_DATA)
    assert len(items) == len(MENU_DATA)


def test_off_menu_returns_empty():
    assert retrieve_relevant_items("do you sell sushi?", MENU_DATA) == []


def test_nut_allergy_excludes_nut_items():
    items = retrieve_relevant_items("I have a nut allergy, what can I eat?", MENU_DATA)
    assert all("contains-nuts" not in i["dietary_tags"] for i in items)
    assert "Almond Croissant" not in names(items)


def test_dairy_free_filter():
    items = retrieve_relevant_items("what is dairy-free?", MENU_DATA)
    expected = {i["name"] for i in MENU_DATA if "dairy-free" in i["dietary_tags"]}
    assert names(items) == expected


def test_topk_cap_for_keyword_queries():
    items = retrieve_relevant_items("something cold and sweet", MENU_DATA)
    assert 0 < len(items) <= 5


@pytest.mark.parametrize("query", ["the", "  ", "!!!"])
def test_empty_token_queries_return_empty(query):
    assert retrieve_relevant_items(query, MENU_DATA) == []


@pytest.mark.parametrize("query", [
    "best recommendation for lunch?",
    "what do you recommend?",
    "I'm hungry, what's good?",
    "what should I get for dinner?",
])
def test_recommendation_queries_ground_on_full_menu(query):
    # Vague recommendation intents must NOT come back empty — they ground on the
    # whole menu so the assistant can suggest real items.
    assert len(retrieve_relevant_items(query, MENU_DATA)) == len(MENU_DATA)


@pytest.mark.parametrize("query", ["do you sell sushi?", "do you have ramen?", "got any tacos?"])
def test_off_menu_requests_still_empty(query):
    # Genuinely off-menu items must still retrieve nothing (-> apology preserved).
    assert retrieve_relevant_items(query, MENU_DATA) == []
