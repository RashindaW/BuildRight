"""Admin 'ask your data' persona — wraps the analytics services as read-only LLM tools.

The same streaming tool-loop (service.stream_chat) powers this; it's just handed a
different system prompt + toolset. Every tool is a pure read of existing analytics, so
there is nothing to ground against (the price guardrail is disabled for this persona,
since the answers legitimately quote revenue/margins).
"""

from __future__ import annotations

import json

from app.services import analytics_service, eval_service

ADMIN_SYSTEM_PROMPT = (
    "You are the BuildRight AI business analyst, helping a store manager understand "
    "performance. Answer ONLY from the analytics tools below — never invent a number.\n"
    "- Pick the single most relevant tool for the question; call more only if needed.\n"
    "- Monetary values from the tools are integer CENTS. Convert to dollars (e.g. 12345 -> "
    "$123.45) before stating them.\n"
    "- Be concise and concrete: lead with the headline number, then one short insight. Use a "
    "compact markdown table or bullets when listing several things.\n"
    "- If the question is not about store performance (sales, margins, inventory, the AI "
    "assistant's cost/quality, or customer satisfaction), say you focus on store analytics."
)


def _days(inp: dict) -> int:
    try:
        d = int(inp.get("days", 30))
    except (TypeError, ValueError):
        d = 30
    return max(1, min(365, d))


_DAYS_SCHEMA = {
    "type": "object",
    "properties": {"days": {"type": "integer", "description": "look-back window in days (1-365)"}},
}

INVENTORY_TOOL = {
    "name": "get_inventory",
    "description": "Current inventory health: total products, in/out-of-stock and low-stock counts, "
    "inventory value (cost and retail), the lowest-stock items, and a per-category breakdown.",
    "input_schema": {"type": "object", "properties": {}},
}
MARGINS_TOOL = {
    "name": "get_margins",
    "description": "Revenue, cost of goods, gross profit and margin % — overall and by category — over the last N days.",
    "input_schema": _DAYS_SCHEMA,
}
ATTRIBUTION_TOOL = {
    "name": "get_ai_attribution",
    "description": "Sales the AI chat assistant drove: chat-sourced orders and revenue, their share of the total, and top chat-driven products.",
    "input_schema": _DAYS_SCHEMA,
}
AI_OPS_TOOL = {
    "name": "get_ai_ops",
    "description": "AI operations: assistant turns, token/cost totals, model + route mix, escalation rate, guardrail-violation rate, and tool usage.",
    "input_schema": _DAYS_SCHEMA,
}
CSAT_TOOL = {
    "name": "get_csat",
    "description": "Customer satisfaction for the chat assistant: response count, average score, 1-5 histogram, and recent comments.",
    "input_schema": _DAYS_SCHEMA,
}
QUALITY_TOOL = {
    "name": "get_chat_quality",
    "description": "Offline chat-quality scores (price-faithfulness, answer-relevance, context-utilisation) for recent assistant answers.",
    "input_schema": {
        "type": "object",
        "properties": {"limit": {"type": "integer", "description": "how many recent turns to score (1-200)"}},
    },
}

ADMIN_TOOLS = [INVENTORY_TOOL, MARGINS_TOOL, ATTRIBUTION_TOOL, AI_OPS_TOOL, CSAT_TOOL, QUALITY_TOOL]


def _j(obj) -> tuple[str, None]:
    return json.dumps(obj, default=str), None


ADMIN_EXECUTORS = {
    "get_inventory": lambda inp, ctx: _j(analytics_service.inventory_summary(ctx.db)),
    "get_margins": lambda inp, ctx: _j(analytics_service.margin_summary(ctx.db, days=_days(inp))),
    "get_ai_attribution": lambda inp, ctx: _j(analytics_service.ai_attribution(ctx.db, days=_days(inp))),
    "get_ai_ops": lambda inp, ctx: _j(analytics_service.ai_operations(ctx.db, days=_days(inp))),
    "get_csat": lambda inp, ctx: _j(analytics_service.csat_summary(ctx.db, days=_days(inp))),
    "get_chat_quality": lambda inp, ctx: _j(
        eval_service.evaluate_recent(ctx.db, limit=max(1, min(200, int(inp.get("limit", 50) or 50))))
    ),
}
