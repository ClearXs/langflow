"""make_datasource_username_password_nullable

Revision ID: 2f097b5df9df
Revises: a1b2c3d4e5f6
Create Date: 2025-11-05 09:21:33.533828

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.engine.reflection import Inspector
from langflow.utils import migration


# revision identifiers, used by Alembic.
revision: str = "2f097b5df9df"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make username and password columns nullable in datasource table.

    This allows for datasources like Hive that don't require authentication.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only update table if it exists
    if "datasource" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("datasource")}

        # Check if username and password columns exist and are not nullable
        if "username" in columns and not columns["username"].get("nullable", False):
            # Use batch mode for better compatibility with SQLite
            with op.batch_alter_table("datasource") as batch_op:
                batch_op.alter_column("username", nullable=True)

        if "password" in columns and not columns["password"].get("nullable", False):
            with op.batch_alter_table("datasource") as batch_op:
                batch_op.alter_column("password", nullable=True)


def downgrade() -> None:
    """Revert username and password columns to not nullable.

    Note: This may fail if there are existing NULL values in the database.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only update table if it exists
    if "datasource" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("datasource")}

        # First, update any NULL values to empty strings to prevent constraint violations
        if "username" in columns:
            op.execute("UPDATE datasource SET username = '' WHERE username IS NULL")
            with op.batch_alter_table("datasource") as batch_op:
                batch_op.alter_column("username", nullable=False)

        if "password" in columns:
            op.execute("UPDATE datasource SET password = '' WHERE password IS NULL")
            with op.batch_alter_table("datasource") as batch_op:
                batch_op.alter_column("password", nullable=False)
