"""role_tiers

Revision ID: 020524e025ca
Revises: f158c824f9b7
Create Date: 2026-06-14 02:11:24.197152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '020524e025ca'
down_revision: Union[str, Sequence[str], None] = 'f158c824f9b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD = sa.Enum("customer", "admin", name="user_role")
_NEW = sa.Enum("customer", "store_helper", "manager", "admin", name="user_role")


def upgrade() -> None:
    """Add store_helper + manager to the user_role enum."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'store_helper'")
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'manager'")
    else:
        # SQLite stores the enum as VARCHAR + CHECK; rebuild the column with the new set.
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.alter_column("role", existing_type=_OLD, type_=_NEW, existing_nullable=False)


def downgrade() -> None:
    """Revert any store_helper/manager rows to customer, then narrow the enum (SQLite only)."""
    op.execute("UPDATE users SET role = 'customer' WHERE role IN ('store_helper', 'manager')")
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.alter_column("role", existing_type=_NEW, type_=_OLD, existing_nullable=False)
    # Postgres enum value removal is unsafe/unsupported; leave the extra values in place.
