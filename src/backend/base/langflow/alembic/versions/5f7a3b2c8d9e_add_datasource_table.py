"""Add datasource table.

Revision ID: 5f7a3b2c8d9e
Revises: d37bc4322900, 6e7b581b5648
Create Date: 2025-01-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5f7a3b2c8d9e"
down_revision: str | None = "d37bc4322900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = ("6e7b581b5648",)


def upgrade() -> None:
    """Create datasource table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only create table if it doesn't exist
    if "datasource" not in table_names:
        op.create_table(
            "datasource",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("host", sa.String(), nullable=False),
            sa.Column("port", sa.Integer(), nullable=False),
            sa.Column("database", sa.String(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("password", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_datasource"),
        )

        # Create indexes
        op.create_index(op.f("ix_datasource_name"), "datasource", ["name"], unique=False)


def downgrade() -> None:
    """Drop datasource table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only drop table if it exists
    if "datasource" in table_names:
        op.drop_index(op.f("ix_datasource_name"), table_name="datasource")
        op.drop_table("datasource")
