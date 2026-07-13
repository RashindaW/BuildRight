from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_id


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # A 1-line, best-effort summary of what the customer is looking for (session memory).
    summary: Mapped[str | None] = mapped_column(String(400), nullable=True)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Opaque tool-use payload (Anthropic content blocks) if any
    tool_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    grounded_item_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    grounded_doc_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Per-turn observability telemetry (assistant turns only)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    route: Mapped[str | None] = mapped_column(String(20), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tools_used: Mapped[list | None] = mapped_column(JSON, nullable=True)
    guardrail_violation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Router v2 telemetry (assistant turns): learned difficulty, cascade, realized cost.
    predicted_difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    router_version: Mapped[str | None] = mapped_column(String(8), nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
