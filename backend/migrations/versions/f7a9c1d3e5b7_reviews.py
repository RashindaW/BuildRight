"""product reviews & ratings

Revision ID: f7a9c1d3e5b7
Revises: e5f7a9b1c3d5
Create Date: 2026-06-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a9c1d3e5b7"
down_revision: Union[str, Sequence[str], None] = "e5f7a9b1c3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("menu_item_id", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("author_name", sa.String(length=80), nullable=False, server_default="Anonymous"),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("sentiment", sa.String(length=12), nullable=False, server_default="neutral"),
        sa.Column("verified_purchase", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("menu_item_id", "user_id", name="uq_review_item_user"),
    )
    op.create_index(op.f("ix_reviews_menu_item_id"), "reviews", ["menu_item_id"], unique=False)
    op.create_index(op.f("ix_reviews_user_id"), "reviews", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reviews_user_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_menu_item_id"), table_name="reviews")
    op.drop_table("reviews")
