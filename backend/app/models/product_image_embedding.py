from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id
from app.models.types import EmbeddingType


class ProductImageEmbedding(TimestampMixin, Base):
    """CLIP image embedding for a product (512-dim), powering visual search —
    the third RRF arm alongside lexical + text-vector."""

    __tablename__ = "product_image_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    menu_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType(512), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # image-url hash
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
