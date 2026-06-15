"""product_image_embeddings (CLIP visual arm)

Revision ID: e5f7a9b1c3d5
Revises: d4e6f8a0b2c4
Create Date: 2026-06-15

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.types import EmbeddingType

revision = "e5f7a9b1c3d5"
down_revision = "d4e6f8a0b2c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_image_embeddings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("menu_item_id", sa.String(), nullable=False),
        sa.Column("embedding", EmbeddingType(512), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_image_embeddings_menu_item_id",
        "product_image_embeddings", ["menu_item_id"], unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_product_image_embeddings_menu_item_id", table_name="product_image_embeddings")
    op.drop_table("product_image_embeddings")
