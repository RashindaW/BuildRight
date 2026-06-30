"""product_graph_embeddings (GNN recommender)

Revision ID: a1b3c5d7e9f1
Revises: f7a9c1d3e5b7
Create Date: 2026-06-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.types import EmbeddingType

revision: str = "a1b3c5d7e9f1"
down_revision: Union[str, Sequence[str], None] = "f7a9c1d3e5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_graph_embeddings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("menu_item_id", sa.String(), nullable=False),
        sa.Column("embedding", EmbeddingType(384), nullable=True),
        sa.Column("model_id", sa.String(length=60), nullable=False, server_default="graph-sgc-v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_graph_embeddings_menu_item_id",
        "product_graph_embeddings", ["menu_item_id"], unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_product_graph_embeddings_menu_item_id", table_name="product_graph_embeddings")
    op.drop_table("product_graph_embeddings")
