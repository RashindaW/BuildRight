"""Optional inbound moderation of customer messages.

Flagged + budgeted: only runs when settings.enable_moderation is True. Uses a
fast keyword screen first (free), then optionally a cheap LLM classification.
Returns (allowed, reason).
"""

from __future__ import annotations

import re

from app.core.config import settings

_BLOCK_PATTERNS = [
    re.compile(r"\b(kill|bomb|terror|suicide)\b", re.I),
]

# Generous message length ceiling (abuse / prompt-stuffing guard).
MAX_MESSAGE_CHARS = 2000


def screen_message(text: str) -> tuple[bool, str]:
    if len(text) > MAX_MESSAGE_CHARS:
        return False, "message_too_long"
    if not settings.enable_moderation:
        return True, "ok"
    for pat in _BLOCK_PATTERNS:
        if pat.search(text):
            return False, "content_blocked"
    return True, "ok"
