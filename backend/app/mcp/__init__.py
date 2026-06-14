"""MCP boundary — re-exposes selected read-only assistant tools to external agents."""

from app.mcp.registry import MCP_TOOLS, McpAccessError, dispatch, list_tools

__all__ = ["MCP_TOOLS", "McpAccessError", "dispatch", "list_tools"]
