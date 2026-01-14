"""Add role flags and fix space membership

Revision ID: g5h6i7j8k9l0
Revises: f4g5h6i7j8k9
Create Date: 2026-01-14 01:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "g5h6i7j8k9l0"
down_revision = "f4g5h6i7j8k9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_default and is_system_role columns to roles table
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    # Remove is_default and is_system_role columns from roles table
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.drop_column("is_system_role")
        batch_op.drop_column("is_default")
