"""Anthropic tool definitions + server-side execution for the assistant.

The model calls `search_menu` to look up real items instead of relying on a
pre-computed retrieval. This makes grounding robust to paraphrase ("something
light", "what's good for lunch") while the deterministic price validator still
guarantees no fabricated prices.

execute_search_menu returns (tool_result_json, grounded_items): the JSON is fed
back to the model; grounded_items accumulate into the turn's grounded set that
the output validator checks prices against.
"""

from __future__ import annotations

import json

from app.ai.retrieval import _score_item, _tokenize

MAX_RESULTS = 12

SEARCH_MENU_TOOL = {
    "name": "search_menu",
    "description": (
        "Search the cafe's real menu. Use this before mentioning ANY item or price. "
        "Combine free-text 'query' with optional structured filters. Omit 'query' to "
        "browse by filter alone (e.g. all items in a category, or all vegan items). "
        "Returns matching menu items with their exact prices."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords or a dish/intent, e.g. 'caesar', 'cold sweet drink', 'lunch'.",
            },
            "category": {
                "type": "string",
                "description": "Filter to one category.",
                "enum": ["salad", "sandwich", "pasta", "drink", "dessert",
                         "starter", "pizza", "main", "side", "kids"],
            },
            "dietary": {
                "type": "array",
                "items": {"type": "string",
                          "enum": ["vegan", "vegetarian", "gluten-free", "dairy-free"]},
                "description": "Only items carrying ALL of these dietary tags.",
            },
            "exclude_allergen": {
                "type": "array",
                "items": {"type": "string",
                          "enum": ["gluten", "dairy", "egg", "soy", "tree-nuts",
                                   "peanuts", "shellfish", "fish", "sesame"]},
                "description": "Exclude items containing any of these allergens.",
            },
            "max_price": {"type": "number", "description": "Only items at or below this price (USD)."},
        },
    },
}

TOOLS = [SEARCH_MENU_TOOL]


def _filter(menu: list[dict], inp: dict) -> list[dict]:
    items = list(menu)
    if inp.get("category"):
        items = [i for i in items if i["category"] == inp["category"]]
    for tag in inp.get("dietary") or []:
        items = [i for i in items if tag in i.get("dietary_tags", [])]
    for alg in inp.get("exclude_allergen") or []:
        items = [i for i in items if alg not in i.get("allergens", [])]
    if inp.get("max_price") is not None:
        items = [i for i in items if i["price"] <= float(inp["max_price"])]

    query = (inp.get("query") or "").strip()
    if query:
        tokens = _tokenize(query)
        if tokens:
            scored = [(i, _score_item(i, tokens)) for i in items]
            hits = sorted((p for p in scored if p[1] > 0), key=lambda p: p[1], reverse=True)
            # A query that matches nothing returns empty (so the model apologizes
            # for genuinely off-menu items). For vague asks the model re-searches
            # with a filter or no query (per the tool description).
            items = [i for i, _ in hits]
    return items[:MAX_RESULTS]


def _serialize(items: list[dict]) -> str:
    payload = [
        {
            "name": i["name"],
            "price": f"${i['price']:.2f}",
            "category": i["category"],
            "dietary_tags": i.get("dietary_tags", []),
            "allergens": i.get("allergens", []),
            "description": i["description"],
        }
        for i in items
    ]
    if not payload:
        return json.dumps({"results": [], "note": "No matching items on the menu."})
    return json.dumps({"results": payload})


def execute_search_menu(tool_input: dict, menu: list[dict]) -> tuple[str, list[dict]]:
    """Run search_menu. Returns (json_for_model, grounded_items)."""
    matched = _filter(menu, tool_input or {})
    return _serialize(matched), matched
