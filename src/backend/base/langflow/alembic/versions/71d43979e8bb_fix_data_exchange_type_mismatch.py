"""fix_data_exchange_type_mismatch

Revision ID: 71d43979e8bb
Revises: 9419f291d31b
Create Date: 2025-11-10 11:14:33.066116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.engine.reflection import Inspector
from langflow.utils import migration


# revision identifiers, used by Alembic.
revision: str = '71d43979e8bb'
down_revision: Union[str, None] = '9419f291d31b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix type mismatches in data_exchange and transaction tables for PostgreSQL."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    # Only proceed if using PostgreSQL
    if dialect_name != "postgresql":
        return

    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Fix data_exchange table if it exists
    if "data_exchange" in table_names:
        # Drop the timestamp index first
        indexes = [idx["name"] for idx in inspector.get_indexes("data_exchange")]
        if "ix_data_exchange_timestamp" in indexes:
            op.drop_index("ix_data_exchange_timestamp", table_name="data_exchange")

        # Drop foreign key constraint
        foreign_keys = inspector.get_foreign_keys("data_exchange")
        if any(fk.get("name") == "fk_data_exchange_transaction_id" for fk in foreign_keys):
            op.drop_constraint("fk_data_exchange_transaction_id", "data_exchange", type_="foreignkey")

        # For PostgreSQL, use ALTER COLUMN directly (not batch mode)
        # Convert JSONB to JSON using USING clause to cast the data
        op.execute(sa.text("""
            ALTER TABLE data_exchange
            ALTER COLUMN data_sample TYPE JSON USING data_sample::text::json
        """))

        op.execute(sa.text("""
            ALTER TABLE data_exchange
            ALTER COLUMN exchange_metadata TYPE JSON USING exchange_metadata::text::json
        """))

        op.execute(sa.text("""
            ALTER TABLE data_exchange
            ALTER COLUMN timestamp TYPE TIMESTAMP USING timestamp::timestamp
        """))

    # Fix transaction table if it exists
    if "transaction" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("transaction")}

        if "downstream_vertices" in columns:
            # Convert JSONB to JSON
            op.execute(sa.text("""
                ALTER TABLE transaction
                ALTER COLUMN downstream_vertices TYPE JSON USING downstream_vertices::text::json
            """))


def downgrade() -> None:
    """Revert type changes back to PostgreSQL-specific types."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    # Only proceed if using PostgreSQL
    if dialect_name != "postgresql":
        return

    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Revert data_exchange table changes
    if "data_exchange" in table_names:
        # Convert JSON back to JSONB
        op.execute(sa.text("""
            ALTER TABLE data_exchange
            ALTER COLUMN data_sample TYPE JSONB USING data_sample::text::jsonb
        """))

        op.execute(sa.text("""
            ALTER TABLE data_exchange
            ALTER COLUMN exchange_metadata TYPE JSONB USING exchange_metadata::text::jsonb
        """))

        op.execute(sa.text("""
            ALTER TABLE data_exchange
            ALTER COLUMN timestamp TYPE TIMESTAMP WITH TIME ZONE USING timestamp AT TIME ZONE 'UTC'
        """))

        # Recreate foreign key constraint
        op.create_foreign_key(
            "fk_data_exchange_transaction_id",
            "data_exchange",
            "transaction",
            ["transaction_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # Recreate timestamp index
        op.create_index("ix_data_exchange_timestamp", "data_exchange", ["timestamp"], unique=False)

    # Revert transaction table changes
    if "transaction" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("transaction")}

        if "downstream_vertices" in columns:
            # Convert JSON back to JSONB
            op.execute(sa.text("""
                ALTER TABLE transaction
                ALTER COLUMN downstream_vertices TYPE JSONB USING downstream_vertices::text::jsonb
            """))
