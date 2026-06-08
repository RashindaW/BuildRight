"""Model/config constants for the assistant."""

from __future__ import annotations

from app.core.config import settings

MODEL = settings.llm_model
MAX_TOKENS = settings.llm_max_tokens
TEMPERATURE = settings.llm_temperature

API_ERROR_MESSAGE = (
    "Sorry, I'm having trouble connecting right now. Please try again in a moment."
)
