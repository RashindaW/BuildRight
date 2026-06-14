"""MCP tool registry + dispatcher.

Only a curated, READ-ONLY subset of the assistant's tools is exposed to external
agents — product/policy search and recommendations. Cart/order/preference
mutations and anything user-scoped are intentionally NOT exposed: internal
executors assume a trusted ToolContext, so the boundary here re-checks access
and constructs a minimal anonymous context (no user_id, no session) for each call.

`dispatch` is plain and synchronous so it can be unit-tested without the MCP SDK;
server.py wraps it for a real stdio MCP transport when the `mcp` package is present.
"""

from __future__ import annotations

from app.ai import tools as _tools
from app.ai.context import ToolContext
from app.models.user import ROLE_RANK


class McpAccessError(Exception):
    """Raised when a tool is unknown or the caller's role is insufficient."""


# name -> (executor, description, input_schema, min_role)
_REGISTRY = {
    "search_products": (
        _tools.execute_search_products,
        _tools.SEARCH_PRODUCTS_TOOL["description"],
        _tools.SEARCH_PRODUCTS_TOOL["input_schema"],
        "customer",
    ),
    "search_knowledge_base": (
        _tools.execute_search_kb,
        _tools.SEARCH_KNOWLEDGE_BASE_TOOL["description"],
        _tools.SEARCH_KNOWLEDGE_BASE_TOOL["input_schema"],
        "customer",
    ),
    "recommend_similar": (
        _tools.execute_recommend_similar,
        _tools.RECOMMEND_SIMILAR_TOOL["description"],
        _tools.RECOMMEND_SIMILAR_TOOL["input_schema"],
        "customer",
    ),
    "frequently_bought_with": (
        _tools.execute_frequently_bought_with,
        _tools.FREQUENTLY_BOUGHT_WITH_TOOL["description"],
        _tools.FREQUENTLY_BOUGHT_WITH_TOOL["input_schema"],
        "customer",
    ),
}

MCP_TOOLS = tuple(_REGISTRY.keys())

# Minimum tier an external caller is granted. "customer" = public read access.
_DEFAULT_ROLE = "customer"


def list_tools() -> list[dict]:
    """MCP-style tool descriptors for discovery."""
    return [
        {"name": name, "description": desc, "input_schema": schema}
        for name, (_, desc, schema, _role) in _REGISTRY.items()
    ]


def dispatch(name: str, arguments: dict, db, *, role: str = _DEFAULT_ROLE) -> str:
    """Run an exposed tool under boundary RBAC. Returns the tool's JSON string.

    Raises McpAccessError for an unknown tool or insufficient role. The constructed
    context is anonymous and read-only (no user_id / session_id).
    """
    entry = _REGISTRY.get(name)
    if entry is None:
        raise McpAccessError(f"Tool '{name}' is not exposed over MCP.")
    executor, _desc, _schema, min_role = entry
    if ROLE_RANK.get(role, -1) < ROLE_RANK[min_role]:
        raise McpAccessError(f"Tool '{name}' requires '{min_role}' access.")

    ctx = ToolContext(menu=[], db=db, user_id=None, session_id=None)
    result_json, _payload = executor(arguments or {}, ctx)
    return result_json
