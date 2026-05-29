from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    model_config = {"extra": "forbid"}
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    messages: list[MessageOut] = []
