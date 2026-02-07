"""Add periodic indexing fields to connectors

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-01-20 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "h6i7j8k9l0m1"
down_revision = "g5h6i7j8k9l0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add periodic indexing fields to connectors table
    with op.batch_alter_table("connectors", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("periodic_indexing_enabled", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("indexing_frequency_minutes", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("next_scheduled_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("is_indexable", sa.Boolean(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    # Remove periodic indexing fields from connectors table
    with op.batch_alter_table("connectors", schema=None) as batch_op:
        batch_op.drop_column("last_indexed_at")
        batch_op.drop_column("is_indexable")
        batch_op.drop_column("next_scheduled_at")
        batch_op.drop_column("indexing_frequency_minutes")
        batch_op.drop_column("periodic_indexing_enabled")
