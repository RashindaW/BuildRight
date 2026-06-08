from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id
from app.models.types import EmbeddingType


class ProductEmbedding(TimestampMixin, Base):
    __tablename__ = "product_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    menu_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType(384), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
