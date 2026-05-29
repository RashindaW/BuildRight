"""Conversation history -> Anthropic messages, windowed.

We re-ground every turn (the MENU block is injected into the *current* user
turn), so historical turns are stored as plain text. This keeps the guardrail
behavior identical to the single-turn PoC and avoids tool-pair reconstruction
hazards. Only the last MAX_TURNS message pairs are kept in the window.
"""

from __future__ import annotations

MAX_TURNS = 12  # keep the last ~12 messages


def build_prior_messages(messages: list) -> list[dict]:
    windowed = messages[-MAX_TURNS:]
    out: list[dict] = []
    for m in windowed:
        if m.role not in ("user", "assistant"):
            continue
        if not m.content:
            continue
        out.append({"role": m.role, "content": m.content})
    # Anthropic requires the sequence to start with a user message.
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out
