from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id
from app.models.types import EmbeddingType


class ProductGraphEmbedding(TimestampMixin, Base):
    """A GNN / graph-propagated item embedding: content features (384-d) smoothed over
    the user co-purchase graph (SGC/LightGCN-style propagation). Powers the graph-based
    recommender. Built offline at seed time; served torch-free via cosine."""

    __tablename__ = "product_graph_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    menu_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType(384), nullable=True)
    model_id: Mapped[str] = mapped_column(String(60), nullable=False, default="graph-sgc-v1")
