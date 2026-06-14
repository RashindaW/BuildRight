"""Stdio MCP server exposing BuildRight's read-only catalog tools.

Run:  python -m app.mcp.server

Requires the `mcp` package (pip install mcp). The actual tool logic lives in
registry.dispatch so it stays unit-testable without the SDK. Stripe payment ops
(refunds, PI lookups) are intended to be served by the official Stripe MCP server
configured alongside this one for staff/admin — not re-implemented here.
"""

from __future__ import annotations

import json

from app.core.db import SessionLocal
from app.mcp import registry


def _run_tool(name: str, arguments: dict) -> str:
    db = SessionLocal()
    try:
        return registry.dispatch(name, arguments, db)
    finally:
        db.close()


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:  # pragma: no cover - exercised only without the SDK
        raise SystemExit(
            "The 'mcp' package is required to run the MCP server: pip install mcp"
        )

    server = FastMCP("buildright-catalog")

    for spec in registry.list_tools():
        name = spec["name"]

        def _make(tool_name: str):
            def _handler(arguments: dict | None = None) -> str:
                return _run_tool(tool_name, arguments or {})
            _handler.__name__ = tool_name
            _handler.__doc__ = spec["description"]
            return _handler

        server.add_tool(_make(name), name=name, description=spec["description"])

    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()
