"""drop product_graph_embeddings (graph recommender removed)

The SGC/LightGCN-style graph recommender was measured against the co-occurrence
baseline it was meant to improve on and lost: recall@5 0.47 vs 1.00, at ~1000ms vs
~32ms per call. Root cause was structural — 95% of products never appeared in a
basket, so their "graph" vector stayed equal to the content vector they were seeded
with, and the model returned near-duplicate substitutes labelled as complements.

Revision ID: c7e9a1b3d5f7
Revises: b4d6f8a0c2e4
Create Date: 2026-09-06
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7e9a1b3d5f7"
down_revision: Union[str, Sequence[str], None] = "b4d6f8a0c2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "product_graph_embeddings" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_product_graph_embeddings_menu_item_id",
                  table_name="product_graph_embeddings")
    op.drop_table("product_graph_embeddings")


def downgrade() -> None:
    """Recreate the empty table. The vectors themselves are rebuilt by a seed step that
    no longer exists, so this restores the schema only."""
    from app.models.types import EmbeddingType

    op.create_table(
        "product_graph_embeddings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("menu_item_id", sa.String(), nullable=False),
        sa.Column("embedding", EmbeddingType(384), nullable=True),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_graph_embeddings_menu_item_id",
                    "product_graph_embeddings", ["menu_item_id"], unique=True)
