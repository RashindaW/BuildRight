"""conversation feedback (CSAT)

Revision ID: b2c4d6e8f0a1
Revises: 7f3a9c2b1d4e
Create Date: 2026-06-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c4d6e8f0a1'
down_revision: Union[str, Sequence[str], None] = '7f3a9c2b1d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversation_feedback',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id', name='uq_feedback_conversation'),
    )
    op.create_index(op.f('ix_conversation_feedback_conversation_id'),
                    'conversation_feedback', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_feedback_user_id'),
                    'conversation_feedback', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_conversation_feedback_user_id'), table_name='conversation_feedback')
    op.drop_index(op.f('ix_conversation_feedback_conversation_id'), table_name='conversation_feedback')
    op.drop_table('conversation_feedback')
