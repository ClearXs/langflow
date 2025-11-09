"""add_advanced_config_to_datasource

Revision ID: 9419f291d31b
Revises: 2f097b5df9df
Create Date: 2025-11-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = "9419f291d31b"
down_revision: Union[str, None] = "2f097b5df9df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add advanced_config column to datasource table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only update table if it exists
    if "datasource" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("datasource")}

        # Add advanced_config column if it doesn't exist
        if "advanced_config" not in columns:
            with op.batch_alter_table("datasource") as batch_op:
                # Use TEXT type for compatibility with both SQLite and PostgreSQL
                batch_op.add_column(
                    sa.Column(
                        "advanced_config",
                        sa.Text(),
                        nullable=True,
                        server_default=sa.text("'{}'")  # Default to empty JSON object
                    )
                )

            # Update existing rows to have empty JSON object if NULL
            op.execute("UPDATE datasource SET advanced_config = '{}' WHERE advanced_config IS NULL")


def downgrade() -> None:
    """Remove advanced_config column from datasource table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only update table if it exists
    if "datasource" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("datasource")}

        # Drop advanced_config column if it exists
        if "advanced_config" in columns:
            with op.batch_alter_table("datasource") as batch_op:
                batch_op.drop_column("advanced_config")
