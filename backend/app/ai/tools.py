"""Tool definitions + server-side executors for the BuildRight Hardware assistant.

Three tools:
  search_products    — hybrid (lexical + vector) product search (live app)
  search_knowledge_base — hybrid KB search over policy/FAQ docs (live app)
  search_menu        — legacy cafe tool; kept for golden-test backward compat only

execute_* functions return (tool_result_json, payload):
  search_products / search_menu  →  payload = list[dict] (grounded item dicts)
  search_knowledge_base          →  payload = list[ChunkHit]
"""

from __future__ import annotations

import json
import re

from app.ai.retrieval import _score_item, _tokenize

MAX_RESULTS = 12
MAX_QTY = 99  # matches schemas/cart.py CartItemIn (le=99)


def _as_int(v, default: int) -> int:
    """Coerce a model-supplied value to int, falling back to default on garbage.

    Tool inputs are whatever the model emits and are not re-validated by the schema,
    so '5 orders', 1.5, or 'all' must not raise out of an executor.
    """
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ---- Legacy cafe tool (backward compat for golden tests) ------------------

SEARCH_MENU_TOOL = {
    "name": "search_menu",
    "description": (
        "Search the cafe's real menu. Use this before mentioning ANY item or price. "
        "Combine free-text 'query' with optional structured filters."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "category": {
                "type": "string",
                "enum": ["salad", "sandwich", "pasta", "drink", "dessert",
                         "starter", "pizza", "main", "side", "kids"],
            },
            "dietary": {
                "type": "array",
                "items": {"type": "string",
                          "enum": ["vegan", "vegetarian", "gluten-free", "dairy-free"]},
            },
            "exclude_allergen": {
                "type": "array",
                "items": {"type": "string",
                          "enum": ["gluten", "dairy", "egg", "soy", "tree-nuts",
                                   "peanuts", "shellfish", "fish", "sesame"]},
            },
            "max_price": {"type": "number"},
        },
    },
}


# ---- Retail tools (live app) ----------------------------------------------

SEARCH_PRODUCTS_TOOL = {
    "name": "search_products",
    "description": (
        "Search BuildRight Hardware's product catalog (1000+ items). Call this BEFORE "
        "mentioning any product, price, SKU, or stock level. Combine a free-text 'query' "
        "with optional filters. You can search by product SKU (e.g. 'BR-PWR-04821'), by "
        "keywords ('cordless drill'), or by need ('something to cut plywood'). Returns "
        "matching products with their SKU, exact price, and availability."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A SKU (e.g. 'BR-PWR-04821'), keywords ('cordless drill'), or an intent ('cut plywood').",
            },
            "category": {
                "type": "string",
                "description": "Limit to one product category.",
                "enum": [
                    "power-tools", "hand-tools", "hardware", "automotive",
                    "kitchen", "outdoor", "cleaning", "paint", "electrical",
                    "plumbing", "seasonal",
                ],
            },
            "tags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["cordless", "corded", "battery-powered", "outdoor",
                             "indoor", "professional", "sale", "new-arrival"],
                },
                "description": "Only items carrying ALL of these tags.",
            },
            "max_price": {
                "type": "number",
                "description": "Only items at or below this price (CAD).",
            },
            "in_stock_only": {
                "type": "boolean",
                "description": "If true (default), exclude out-of-stock items.",
            },
        },
    },
}

SEARCH_KNOWLEDGE_BASE_TOOL = {
    "name": "search_knowledge_base",
    "description": (
        "Search BuildRight Hardware's policy and FAQ knowledge base. Call this BEFORE "
        "answering any question about returns, refunds, warranty, shipping, price-match, "
        "or store policies. Always cite the source in your answer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Policy question or topic, e.g. 'how many days to return an item'.",
            },
            "topic": {
                "type": "string",
                "description": "Optional: narrow to one policy area.",
                "enum": ["returns", "refunds", "warranty", "shipping",
                         "price-match", "faq", "store-policies"],
            },
        },
        "required": ["query"],
    },
}

GET_ORDER_HISTORY_TOOL = {
    "name": "get_order_history",
    "description": (
        "Retrieve the logged-in user's past orders. Use this when the user asks what they "
        "previously bought, wants to reorder, or references a past purchase."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": "How far back to look.",
                "enum": ["last_week", "last_month", "last_3_months", "last_year"],
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of orders to return (default 5).",
            },
        },
    },
}

REORDER_TOOL = {
    "name": "reorder",
    "description": (
        "Add a previously ordered item to the user's current cart. "
        "Call get_order_history first to find the item slug, then call this tool."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "menu_item_id": {
                "type": "string",
                "description": "The item slug or id from order history.",
            },
            "quantity": {
                "type": "integer",
                "description": "How many to add (default 1).",
            },
        },
        "required": ["menu_item_id"],
    },
}

GET_PREFERENCES_TOOL = {
    "name": "get_preferences",
    "description": "Retrieve the logged-in user's saved preferences (brand, tool-type, etc.).",
    "input_schema": {"type": "object", "properties": {}},
}

SET_PREFERENCE_TOOL = {
    "name": "set_preference",
    "description": (
        "Save a user preference (e.g. preferred brand, favourite category). "
        "Call this when the user explicitly expresses a product preference."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Preference name, e.g. 'preferred_brand'."},
            "value": {"type": "string", "description": "Preference value, e.g. 'Mastercraft'."},
        },
        "required": ["key", "value"],
    },
}

# Exposed to the model in the live retail app
TOOLS = [
    SEARCH_PRODUCTS_TOOL,
    SEARCH_KNOWLEDGE_BASE_TOOL,
    GET_ORDER_HISTORY_TOOL,
    REORDER_TOOL,
    GET_PREFERENCES_TOOL,
    SET_PREFERENCE_TOOL,
]


# ---- Shared serialisers ---------------------------------------------------

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
            items = [i for i, _ in hits]
    return items[:MAX_RESULTS]


def _stock_label(i: dict) -> str:
    if not i.get("is_available", True) or i.get("stock_qty", 0) <= 0:
        return "out of stock"
    qty = i.get("stock_qty", 0)
    return f"{qty} in stock" if qty <= 15 else "in stock"


def _serialize(items: list[dict]) -> str:
    payload = [
        {
            "sku": i.get("sku"),
            "name": i["name"],
            "price": f"${i['price']:.2f}",
            "category": i["category"],
            "availability": _stock_label(i),
            "tags": i.get("dietary_tags", []),
            "description": i["description"],
        }
        for i in items
    ]
    if not payload:
        return json.dumps({"results": [], "note": "No matching products found."})
    return json.dumps({"results": payload})


# ---- Executors -----------------------------------------------------------

def execute_search_menu(tool_input: dict, menu: list[dict]) -> tuple[str, list[dict]]:
    """Legacy cafe executor. Returns (json_for_model, grounded_items)."""
    matched = _filter(menu, tool_input or {})
    return _serialize(matched), matched


def execute_search_products(tool_input: dict, ctx) -> tuple[str, list[dict]]:
    """Retail product search via hybrid retrieval. ctx is a ToolContext."""
    from app.ai.hybrid import hybrid_search_products

    inp = tool_input or {}
    filters = {}
    if inp.get("category"):
        filters["category"] = inp["category"]
    if inp.get("tags"):
        filters["tags"] = inp["tags"]
    if inp.get("max_price") is not None:
        filters["max_price"] = inp["max_price"]
    filters["in_stock_only"] = inp.get("in_stock_only", True)

    items = hybrid_search_products(ctx.db, inp.get("query", ""), filters=filters, k=MAX_RESULTS)
    return _serialize(items), items


_TOPIC_TO_DOC_TYPE = {
    "returns": "policy",
    "refunds": "policy",
    "store-policies": "policy",
    "warranty": "warranty",
    "shipping": "shipping",
    "price-match": "price-match",
    "faq": "faq",
}


_LOGIN_REQUIRED = json.dumps({"error": "login_required", "message": "Please log in to access your order history and preferences."})

_PERIOD_DAYS = {
    "last_week": 7,
    "last_month": 30,
    "last_3_months": 90,
    "last_year": 365,
}


def execute_get_order_history(tool_input: dict, ctx) -> tuple[str, list]:
    if not ctx.user_id:
        return _LOGIN_REQUIRED, []
    from datetime import datetime, timedelta, timezone
    from app.services.order_service import list_orders_since

    inp = tool_input or {}
    days = _PERIOD_DAYS.get(inp.get("period", "last_month"), 30)
    limit = min(_as_int(inp.get("limit"), 5), 20)
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    orders = list_orders_since(ctx.db, ctx.user_id, since)[:limit]

    if not orders:
        return json.dumps({"orders": [], "note": "No orders found in that period."}), []

    result = []
    grounded: list[dict] = []
    for o in orders:
        items = []
        for i in o.items:
            items.append({
                "name": i.name_snapshot,
                "slug": i.menu_item_id,
                "quantity": i.quantity,
                "unit_price": f"${i.unit_price_cents / 100:.2f}",
            })
            # Ground past-purchase prices so the price validator accepts them when
            # the assistant restates what the customer paid.
            grounded.append({"id": i.menu_item_id or i.name_snapshot,
                             "name": i.name_snapshot, "price": i.unit_price_cents / 100})
        grounded.append({"id": o.order_number, "name": o.order_number,
                         "price": o.total_cents / 100})
        result.append({
            "order_number": o.order_number,
            "date": o.created_at.strftime("%Y-%m-%d"),
            "status": o.status,
            "total": f"${o.total_cents / 100:.2f}",
            "items": items,
        })
    return json.dumps({"orders": result}), grounded


def execute_reorder(tool_input: dict, ctx) -> tuple[str, dict]:
    if not ctx.user_id:
        return _LOGIN_REQUIRED, {"added": False}
    from datetime import datetime, timedelta, timezone
    from app.services.cart_service import _resolve_item, add_item
    from app.services.order_service import list_orders_since
    from app.core.errors import AppError, NotFoundError

    inp = tool_input or {}
    raw = (inp.get("menu_item_id") or "").strip()
    quantity = max(1, min(_as_int(inp.get("quantity"), 1), MAX_QTY))
    if not raw:
        return json.dumps({"error": "menu_item_id is required"}), {"added": False}

    try:
        # Resolve the model-supplied id/slug to a concrete catalog item.
        item = _resolve_item(ctx.db, raw)
        # Bind reorder to the user's OWN purchase history: the model must have
        # surfaced this item via get_order_history, not pick an arbitrary catalog id.
        since = datetime.now(tz=timezone.utc) - timedelta(days=365)
        orders = list_orders_since(ctx.db, ctx.user_id, since)
        ordered_ids = {oi.menu_item_id for o in orders for oi in o.items if oi.menu_item_id}
        if item.id not in ordered_ids:
            return json.dumps({"error": "not_in_history",
                               "message": "That item isn't in your recent order history."}), {"added": False}

        add_item(ctx.db, ctx.user_id, item.id, quantity, [])
        return json.dumps({"added": True, "quantity": quantity, "item": item.slug}), {"added": True}
    except (AppError, NotFoundError) as e:
        return json.dumps({"error": str(e)}), {"added": False}


def execute_get_preferences(tool_input: dict, ctx) -> tuple[str, dict]:
    if not ctx.user_id:
        return _LOGIN_REQUIRED, {}
    from app.services.memory_service import get_preferences
    prefs = get_preferences(ctx.db, ctx.user_id)
    return json.dumps({"preferences": prefs}), prefs


_CONTROL_CHARS_RE = re.compile(r"[\r\n\t\x00-\x1f\x7f]+")


def _sanitize_pref(text: str, limit: int) -> str:
    """Collapse control/newline chars to spaces and truncate. Prevents a stored
    preference from injecting new lines/instructions into the prompt preamble."""
    return _CONTROL_CHARS_RE.sub(" ", str(text or "")).strip()[:limit]


def execute_set_preference(tool_input: dict, ctx) -> tuple[str, dict]:
    if not ctx.user_id:
        return _LOGIN_REQUIRED, {}
    from app.services.memory_service import set_preference
    from app.safety.injection import looks_like_injection

    inp = tool_input or {}
    key = _sanitize_pref(inp.get("key"), 80)
    value = _sanitize_pref(inp.get("value"), 200)
    if not key:
        return json.dumps({"error": "key is required"}), {}
    # Stored prefs are injected into future prompts — reject anything that reads
    # like an injection attempt so it can never become persistent instruction text.
    if looks_like_injection(key) or looks_like_injection(value):
        return json.dumps({"error": "preference_rejected",
                           "message": "That preference couldn't be saved."}), {}
    set_preference(ctx.db, ctx.user_id, key, value)
    return json.dumps({"saved": True, "key": key, "value": value}), {key: value}


def execute_search_kb(tool_input: dict, ctx) -> tuple[str, list]:
    """KB policy search via hybrid retrieval. Returns (json_for_model, list[ChunkHit])."""
    from app.ai.hybrid import hybrid_search_kb

    inp = tool_input or {}
    topic = inp.get("topic")
    doc_types = [_TOPIC_TO_DOC_TYPE[topic]] if topic and topic in _TOPIC_TO_DOC_TYPE else None

    chunks = hybrid_search_kb(ctx.db, inp.get("query", ""), doc_types=doc_types)
    if not chunks:
        return json.dumps({"results": [], "note": "No matching policy found. Suggest contacting customer service."}), []

    results = [
        {
            "document": c.doc_title,
            "section": c.heading or "(overview)",
            "content": c.content,
            "cite_as": f"{c.doc_title} › {c.heading}" if c.heading else c.doc_title,
        }
        for c in chunks
    ]
    return json.dumps({"results": results}), chunks
