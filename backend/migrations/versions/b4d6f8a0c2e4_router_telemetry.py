"""router v2 telemetry columns on messages

Revision ID: b4d6f8a0c2e4
Revises: a1b3c5d7e9f1
Create Date: 2026-06-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4d6f8a0c2e4"
down_revision: Union[str, Sequence[str], None] = "a1b3c5d7e9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("predicted_difficulty", sa.Float(), nullable=True))
    op.add_column("messages", sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("messages", sa.Column("router_version", sa.String(length=8), nullable=True))
    op.add_column("messages", sa.Column("cost_usd", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "cost_usd")
    op.drop_column("messages", "router_version")
    op.drop_column("messages", "escalated")
    op.drop_column("messages", "predicted_difficulty")
