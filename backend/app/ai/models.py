"""Model/config constants for the assistant."""

from __future__ import annotations

from app.core.config import settings

MODEL = settings.llm_model
MAX_TOKENS = settings.llm_max_tokens
TEMPERATURE = settings.llm_temperature

# Larger budget for list-style answers (e.g. "what's on the menu?") so the
# complete dietary set is never truncated mid-list.
LIST_MAX_TOKENS = 700

API_ERROR_MESSAGE = (
    "Sorry, I'm having trouble reaching the kitchen right now. Please try again in a moment."
)
