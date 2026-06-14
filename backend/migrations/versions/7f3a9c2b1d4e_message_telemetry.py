"""message telemetry (AI observability)

Revision ID: 7f3a9c2b1d4e
Revises: 5cde14885b8b
Create Date: 2026-06-14 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3a9c2b1d4e'
down_revision: Union[str, Sequence[str], None] = '5cde14885b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add per-turn observability telemetry to messages."""
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('model', sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column('route', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('tools_used', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('guardrail_violation', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Drop the telemetry columns."""
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_column('guardrail_violation')
        batch_op.drop_column('tools_used')
        batch_op.drop_column('output_tokens')
        batch_op.drop_column('input_tokens')
        batch_op.drop_column('route')
        batch_op.drop_column('model')
