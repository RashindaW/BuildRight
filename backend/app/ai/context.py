"""ToolContext: identity + resources threaded through stream_chat() into all tools."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolContext:
    menu: list[dict]
    db: object         # sqlalchemy.orm.Session — typed as object to avoid circular imports
    user_id: str | None = None
    session_id: str | None = None
    preferences: dict[str, str] = field(default_factory=dict)
