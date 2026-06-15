"""Tool definitions + server-side executors for the BuildRight AI assistant.

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
        "Search BuildRight AI's product catalog (1000+ items). Call this BEFORE "
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
        "Search BuildRight AI's knowledge base: store policies (returns, refunds, "
        "warranty, shipping, price-match) AND product buying guides ('how do I choose', "
        "'what's the difference between X and Y', what each variant/option means). Call this "
        "BEFORE answering any policy question or any advice/how-to-choose question. Always cite the source."
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
        "Add a previously ordered item back to the customer's cart. When the customer asks "
        "to reorder, re-buy, or 'add that again', call THIS tool DIRECTLY — you do NOT need "
        "to call get_order_history or search_products first. Pass whatever the customer "
        "named the item as 'menu_item_id' (a plain product name like 'exterior paint' works, "
        "as do a SKU, slug, or id); reorder looks it up in the customer's own order history. "
        "By default it adds the SAME quantity they originally ordered; if the customer states "
        "a quantity (e.g. 'reorder 10 paints'), pass that as 'quantity'. NEVER ask the "
        "customer to confirm a quantity they already gave — just reorder it. Never say an "
        "item was added unless this tool returned added=true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "menu_item_id": {
                "type": "string",
                "description": "What the customer called the item: a product name ('exterior paint'), "
                               "SKU, slug, or id. reorder matches it against their order history.",
            },
            "quantity": {
                "type": "integer",
                "description": "Optional. Only set this if the customer explicitly asks for a specific "
                               "amount; otherwise omit it and the original order quantity is used.",
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

COMPUTE_MATERIALS_TOOL = {
    "name": "compute_materials",
    "description": (
        "Plan a home-improvement project: turn room measurements into a costed materials "
        "list of real in-stock products. Use this when a shopper describes a project — e.g. "
        "'I want to repair/paint my room', 'tile my bathroom floor', 'install laminate'. "
        "First collect the project type and the room's length and width in feet (and height "
        "for wall projects, default 8 ft); then call this. It returns each material with a "
        "matched product, SKU, exact unit price, quantity and line total, plus a subtotal "
        "and the assumptions used. Present the list and offer to add it with "
        "add_materials_to_cart. Do NOT invent quantities or prices — they come from here."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "project_type": {
                "type": "string",
                "description": "The kind of project.",
                "enum": ["paint_room", "tile_floor", "laminate_floor", "drywall_room"],
            },
            "length_ft": {"type": "number", "description": "Room length in feet."},
            "width_ft": {"type": "number", "description": "Room width in feet."},
            "height_ft": {
                "type": "number",
                "description": "Wall height in feet (wall projects). Defaults to 8.",
            },
            "coats": {
                "type": "integer",
                "description": "Paint coats (paint_room only). Defaults to 2.",
            },
        },
        "required": ["project_type", "length_ft", "width_ft"],
    },
}

ADD_MATERIALS_TO_CART_TOOL = {
    "name": "add_materials_to_cart",
    "description": (
        "Add a list of products to the cart in one call — used after compute_materials when "
        "the shopper confirms they want the materials. Pass the SKU (preferred) or product "
        "name and a quantity for each line. Never say items were added unless this tool "
        "returned them in 'added'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "Products to add.",
                "items": {
                    "type": "object",
                    "properties": {
                        "item": {"type": "string", "description": "SKU, slug, id, or product name."},
                        "quantity": {"type": "integer", "description": "How many (>=1)."},
                    },
                    "required": ["item", "quantity"],
                },
            },
        },
        "required": ["items"],
    },
}

SUGGEST_COMPLEMENTARY_TOOL = {
    "name": "suggest_complementary",
    "description": (
        "Suggest complementary add-on products for a project or a product the shopper is "
        "considering (an upsell). Returns a few in-stock items with their SKU and exact price. "
        "Use after presenting a materials list, or when a shopper adds an item, to recommend "
        "the tools/accessories that go with it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "project_type": {
                "type": "string",
                "description": "Optional project context.",
                "enum": ["paint_room", "tile_floor", "laminate_floor", "drywall_room"],
            },
            "query": {
                "type": "string",
                "description": "Optional free-text need to anchor suggestions, e.g. 'painting a wall'.",
            },
            "item": {
                "type": "string",
                "description": "Optional SKU/slug/name of an item the shopper picked — uses "
                               "real co-purchase data to cross-sell.",
            },
        },
    },
}

RECOMMEND_SIMILAR_TOOL = {
    "name": "recommend_similar",
    "description": (
        "Find products similar to a given item (same category, similar use, similar price). "
        "Use when a shopper asks 'what's like this?', 'show me alternatives', or 'anything "
        "cheaper than this'. Pass the item's SKU, slug, or name. Returns items with SKU + price."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "item": {"type": "string", "description": "SKU, slug, id, or product name to match."},
            "limit": {"type": "integer", "description": "Max results (default 5)."},
        },
        "required": ["item"],
    },
}

FREQUENTLY_BOUGHT_WITH_TOOL = {
    "name": "frequently_bought_with",
    "description": (
        "Find products commonly bought together with a given item, based on real order "
        "history (collaborative filtering). Use for 'what goes with this?' or to cross-sell "
        "at the cart/product page. Pass the item's SKU, slug, or name. Returns items + price."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "item": {"type": "string", "description": "SKU, slug, id, or product name to anchor on."},
            "limit": {"type": "integer", "description": "Max results (default 5)."},
        },
        "required": ["item"],
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
    COMPUTE_MATERIALS_TOOL,
    ADD_MATERIALS_TO_CART_TOOL,
    SUGGEST_COMPLEMENTARY_TOOL,
    RECOMMEND_SIMILAR_TOOL,
    FREQUENTLY_BOUGHT_WITH_TOOL,
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
    from sqlalchemy import select, func
    from app.services.cart_service import _resolve_item, add_item
    from app.services.order_service import list_orders_since
    from app.core.errors import AppError, NotFoundError
    from app.models.menu import MenuItem

    inp = tool_input or {}
    raw = (inp.get("menu_item_id") or "").strip()
    if not raw:
        return json.dumps({"error": "menu_item_id is required"}), {"added": False}

    # Bind reorder to the user's OWN purchase history (orders are newest-first).
    since = datetime.now(tz=timezone.utc) - timedelta(days=365)
    orders = list_orders_since(ctx.db, ctx.user_id, since)
    hist = [(oi.menu_item_id, oi.name_snapshot, oi.quantity)
            for o in orders for oi in o.items if oi.menu_item_id]
    if not hist:
        return json.dumps({"error": "not_in_history",
                           "message": "You have no recent orders to reorder from."}), {"added": False}

    # Resolve the requested identifier (id, slug, SKU, or product name) to a past item.
    target_id = None
    try:
        target_id = _resolve_item(ctx.db, raw).id  # exact id/slug, if still available
    except (AppError, NotFoundError):
        target_id = None
    if target_id is None:
        # SKU, or the id/slug of an out-of-stock item (which _resolve_item rejects)
        mi = ctx.db.execute(
            select(MenuItem).where(
                (func.lower(MenuItem.sku) == raw.lower())
                | (MenuItem.id == raw)
                | (MenuItem.slug == raw.lower())
            )
        ).scalar_one_or_none()
        target_id = mi.id if mi else None
    match = next((h for h in hist if h[0] == target_id), None) if target_id else None
    if match is None:
        rl = raw.lower()
        match = next((h for h in hist if rl in h[1].lower() or h[1].lower() in rl), None)
    if match is None:
        return json.dumps({"error": "not_in_history",
                           "message": "That item isn't in your recent order history."}), {"added": False}

    menu_item_id, name, original_qty = match
    # Quantity: honour an explicit amount; otherwise replay the original order quantity.
    qty_arg = inp.get("quantity")
    if qty_arg is not None:
        quantity = max(1, min(_as_int(qty_arg, original_qty), MAX_QTY))
    else:
        quantity = max(1, min(original_qty, MAX_QTY))

    try:
        add_item(ctx.db, ctx.user_id, menu_item_id, quantity, [])
        # Attribute this cart to the chat conversation that drove the add.
        from app.services.cart_service import mark_cart_source
        mark_cart_source(ctx.db, ctx.user_id, "chat", getattr(ctx, "conversation_id", None))
    except (AppError, NotFoundError) as e:
        return json.dumps({"error": "unavailable", "message": str(e)}), {"added": False}

    # Ground the item's current unit + line-total price so the assistant can state them.
    mi = ctx.db.execute(select(MenuItem).where(MenuItem.id == menu_item_id)).scalar_one_or_none()
    grounded = []
    if mi:
        grounded = [
            {"id": mi.slug, "name": mi.name, "price": mi.price_cents / 100},
            {"id": f"{mi.slug}:line", "name": mi.name, "price": (mi.price_cents * quantity) / 100},
        ]
    return json.dumps({"added": True, "quantity": quantity, "item": name}), {"added": True, "grounded": grounded}


# ---- Project planning (Phase 2.1) -----------------------------------------

def _resolve_menu_item(db, raw: str):
    """Resolve a SKU / slug / id / exact-ish name to a MenuItem, or None."""
    from sqlalchemy import select, func
    from app.models.menu import MenuItem

    raw = (raw or "").strip()
    if not raw:
        return None
    mi = db.execute(
        select(MenuItem).where(
            (func.lower(MenuItem.sku) == raw.lower())
            | (MenuItem.id == raw)
            | (MenuItem.slug == raw.lower())
        )
    ).scalar_one_or_none()
    if mi:
        return mi
    # Fall back to a name contains-match (first available).
    return db.execute(
        select(MenuItem).where(func.lower(MenuItem.name).contains(raw.lower()))
        .where(MenuItem.is_available.is_(True))
    ).scalars().first()


def execute_compute_materials(tool_input: dict, ctx) -> tuple[str, list[dict] | None]:
    """Compute a project's bill of materials and resolve each role to a real SKU."""
    from app.ai.projects import plan_materials, ProjectPlanError, PROJECT_TYPES
    from app.ai.hybrid import hybrid_search_products

    inp = tool_input or {}
    project_type = (inp.get("project_type") or "").strip()
    params = {
        "length_ft": inp.get("length_ft"),
        "width_ft": inp.get("width_ft"),
        "height_ft": inp.get("height_ft"),
        "coats": inp.get("coats"),
    }
    try:
        plan = plan_materials(project_type, params)
    except ProjectPlanError as e:
        return json.dumps({
            "error": "invalid_project", "message": str(e),
            "supported": list(PROJECT_TYPES),
        }), None

    lines: list[dict] = []
    grounded: list[dict] = []
    subtotal_cents = 0
    for m in plan["materials"]:
        filters = {"in_stock_only": True}
        if m["category"]:
            filters["category"] = m["category"]
        hits = hybrid_search_products(ctx.db, m["query"], filters=filters, k=3)
        if not hits:  # retry without the category constraint
            hits = hybrid_search_products(ctx.db, m["query"], filters={"in_stock_only": True}, k=3)
        if not hits:
            lines.append({
                "role": m["role"], "label": m["label"], "unit": m["unit"],
                "quantity": m["quantity"], "available": False,
                "note": "No in-stock match — substitute manually.",
            })
            continue
        pick = hits[0]
        slug = pick.get("slug") or pick.get("id")
        unit_price = float(pick["price"])
        qty = int(m["quantity"])
        line_total = round(unit_price * qty, 2)
        subtotal_cents += round(line_total * 100)
        lines.append({
            "role": m["role"], "label": m["label"], "unit": m["unit"],
            "product": pick["name"], "sku": pick.get("sku"), "slug": slug,
            "quantity": qty, "unit_price": f"${unit_price:.2f}",
            "line_total": f"${line_total:.2f}", "optional": m["optional"],
        })
        # Ground unit + line-total so the assistant can quote them past the guardrail.
        grounded.append({"id": slug, "name": pick["name"], "price": unit_price})
        grounded.append({"id": f"{slug}:line", "name": pick["name"], "price": line_total})

    subtotal = subtotal_cents / 100
    grounded.append({"id": "project_subtotal", "name": "Project subtotal", "price": subtotal})
    return json.dumps({
        "project": plan["label"], "project_type": plan["project_type"],
        "dimensions": plan["dimensions"], "derived": plan["derived"],
        "assumptions": plan["assumptions"], "materials": lines,
        "subtotal": f"${subtotal:.2f}",
        "next_step": "Offer to add these with add_materials_to_cart, then suggest_complementary.",
    }), grounded


def execute_add_materials_to_cart(tool_input: dict, ctx) -> tuple[str, dict]:
    """Add a list of {item, quantity} to the cart (user or guest)."""
    from app.services.cart_service import add_item, mark_cart_source
    from app.core.errors import AppError, NotFoundError

    if not ctx.user_id and not ctx.session_id:
        return _LOGIN_REQUIRED, {"added": False}

    inp = tool_input or {}
    raw_items = inp.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        return json.dumps({"error": "no_items", "message": "Provide items to add."}), {"added": False}

    added, failed, grounded = [], [], []
    for entry in raw_items[:30]:
        if not isinstance(entry, dict):
            continue
        mi = _resolve_menu_item(ctx.db, entry.get("item", ""))
        qty = max(1, min(_as_int(entry.get("quantity"), 1), MAX_QTY))
        if mi is None or not mi.is_available:
            failed.append({"item": entry.get("item"), "reason": "unavailable"})
            continue
        try:
            add_item(ctx.db, ctx.user_id, mi.id, qty, [], session_id=ctx.session_id)
        except (AppError, NotFoundError) as e:
            failed.append({"item": mi.name, "reason": str(e)})
            continue
        line_total = round(mi.price_cents * qty / 100, 2)
        added.append({"product": mi.name, "sku": mi.sku, "quantity": qty,
                      "unit_price": f"${mi.price_cents / 100:.2f}",
                      "line_total": f"${line_total:.2f}"})
        grounded.append({"id": mi.slug, "name": mi.name, "price": mi.price_cents / 100})
        grounded.append({"id": f"{mi.slug}:line", "name": mi.name, "price": line_total})

    if added:
        mark_cart_source(ctx.db, ctx.user_id, "chat",
                         getattr(ctx, "conversation_id", None), session_id=ctx.session_id)
    return json.dumps({"added": added, "failed": failed}), {
        "added": bool(added), "grounded": grounded,
    }


# Curated upsell anchors per project (resolved to live SKUs at call time).
_COMPLEMENTARY = {
    "paint_room": [("sandpaper assortment", "building-materials"),
                   ("safety glasses", "safety"), ("work gloves", "safety")],
    "tile_floor": [("tile cutter", "flooring"), ("knee pads", "safety"),
                   ("safety glasses", "safety")],
    "laminate_floor": [("utility knife", "hand-tools"), ("knee pads", "safety"),
                       ("floor trim baseboard", "flooring")],
    "drywall_room": [("utility knife", "hand-tools"), ("dust masks respirator", "safety"),
                     ("sandpaper assortment", "building-materials")],
}


def execute_suggest_complementary(tool_input: dict, ctx) -> tuple[str, list[dict]]:
    """Return a few complementary in-stock add-ons (an upsell)."""
    from app.ai.hybrid import hybrid_search_products

    inp = tool_input or {}
    seen, suggestions, grounded = set(), [], []

    # Real co-purchase data first when the shopper named a specific item.
    if inp.get("item"):
        from app.services.recommender_service import frequently_bought_with
        for r in frequently_bought_with(ctx.db, inp["item"], k=3):
            seen.add(r["slug"])
            suggestions.append({"product": r["name"], "sku": r["sku"],
                                "price": f"${r['price']:.2f}", "category": r["category"]})
            grounded.append({"id": r["slug"], "name": r["name"], "price": r["price"]})

    anchors = list(_COMPLEMENTARY.get((inp.get("project_type") or "").strip(), []))
    if inp.get("query"):
        anchors.append((inp["query"], None))
    if not anchors and not suggestions:
        anchors = [("safety glasses", "safety"), ("work gloves", "safety")]

    for query, category in anchors:
        filters = {"in_stock_only": True}
        if category:
            filters["category"] = category
        hits = hybrid_search_products(ctx.db, query, filters=filters, k=2)
        if not hits:  # category may be absent in a given catalog — retry unconstrained
            hits = hybrid_search_products(ctx.db, query, filters={"in_stock_only": True}, k=2)
        for pick in hits:
            slug = pick.get("slug") or pick.get("id")
            if slug in seen:
                continue
            seen.add(slug)
            unit_price = float(pick["price"])
            suggestions.append({"product": pick["name"], "sku": pick.get("sku"),
                                "price": f"${unit_price:.2f}", "category": pick["category"]})
            grounded.append({"id": slug, "name": pick["name"], "price": unit_price})
            break  # one pick per anchor keeps the list tight
    if not suggestions:
        return json.dumps({"suggestions": [], "note": "No complementary items found."}), []
    return json.dumps({"suggestions": suggestions}), grounded


# ---- Recommender (Phase 4.2) ----------------------------------------------

def _serialize_recs(recs: list[dict]) -> tuple[str, list[dict]]:
    if not recs:
        return json.dumps({"recommendations": [], "note": "No recommendations found."}), []
    results = [{"product": r["name"], "sku": r["sku"],
                "price": f"${r['price']:.2f}", "reason": r["reason"]} for r in recs]
    grounded = [{"id": r["slug"], "name": r["name"], "price": r["price"]} for r in recs]
    return json.dumps({"recommendations": results}), grounded


def execute_recommend_similar(tool_input: dict, ctx) -> tuple[str, list[dict]]:
    from app.services.recommender_service import recommend_similar
    inp = tool_input or {}
    ref = (inp.get("item") or "").strip()
    if not ref:
        return json.dumps({"error": "item is required"}), []
    recs = recommend_similar(ctx.db, ref, k=min(_as_int(inp.get("limit"), 5), 10))
    return _serialize_recs(recs)


def execute_frequently_bought_with(tool_input: dict, ctx) -> tuple[str, list[dict]]:
    from app.services.recommender_service import frequently_bought_with
    inp = tool_input or {}
    ref = (inp.get("item") or "").strip()
    if not ref:
        return json.dumps({"error": "item is required"}), []
    recs = frequently_bought_with(ctx.db, ref, k=min(_as_int(inp.get("limit"), 5), 10))
    return _serialize_recs(recs)


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

    from app.core.config import settings
    chunks = hybrid_search_kb(ctx.db, inp.get("query", ""), doc_types=doc_types,
                              rerank=settings.rerank_enabled)
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
