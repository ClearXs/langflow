"""Add data exchange tracking table and extend transaction table

Revision ID: a1b2c3d4e5f6
Revises: 1ca035e6ae0a
Create Date: 2025-11-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "1ca035e6ae0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add data_exchange table and extend transaction table with exchange fields."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()
    dialect_name = conn.dialect.name

    # Create data_exchange table if it doesn't exist
    if "data_exchange" not in table_names:
        # Determine JSON and UUID column types based on database dialect
        # Use sa.JSON() for consistency with other tables (avoids JSONB mismatch)
        if dialect_name == "postgresql":
            json_type = sa.JSON()  # Use JSON instead of JSONB for consistency
            uuid_type = sa.UUID()
            timestamp_type = sa.DateTime()  # Use simple DateTime without timezone
        else:
            # SQLite: use TEXT for UUID and JSON compatibility
            json_type = sa.JSON()
            uuid_type = sa.String()  # Use TEXT for UUID in SQLite
            timestamp_type = sa.DateTime()  # Simple DateTime without timezone for SQLite

        op.create_table(
            "data_exchange",
            sa.Column("id", uuid_type, nullable=False),
            sa.Column("timestamp", timestamp_type, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("transaction_id", uuid_type, nullable=False),
            sa.Column("source_vertex_id", sa.String(), nullable=False),
            sa.Column("target_vertex_id", sa.String(), nullable=False),
            sa.Column("exchange_type", sa.String(), nullable=False),
            sa.Column("data_type", sa.String(), nullable=False),
            sa.Column("data_size", sa.Integer(), nullable=False),
            sa.Column("data_sample", json_type, nullable=True),
            sa.Column("exchange_metadata", json_type, nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_data_exchange"),
        )

        # Create indexes for better query performance
        op.create_index(
            op.f("ix_data_exchange_transaction_id"), "data_exchange", ["transaction_id"], unique=False
        )
        op.create_index(
            op.f("ix_data_exchange_source_vertex_id"), "data_exchange", ["source_vertex_id"], unique=False
        )
        op.create_index(
            op.f("ix_data_exchange_target_vertex_id"), "data_exchange", ["target_vertex_id"], unique=False
        )
        op.create_index(op.f("ix_data_exchange_timestamp"), "data_exchange", ["timestamp"], unique=False)

        # For PostgreSQL, add foreign key constraint
        if dialect_name == "postgresql":
            op.create_foreign_key(
                "fk_data_exchange_transaction_id",
                "data_exchange",
                "transaction",
                ["transaction_id"],
                ["id"],
                ondelete="CASCADE",
            )

    # Extend transaction table with exchange fields if they don't exist
    if "transaction" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("transaction")}

        # Add exchange_count column if it doesn't exist
        if "exchange_count" not in columns:
            op.add_column("transaction", sa.Column("exchange_count", sa.Integer(), server_default="0", nullable=False))

        # Add downstream_vertices column if it doesn't exist
        if "downstream_vertices" not in columns:
            # Use sa.JSON() for consistency with other tables
            op.add_column("transaction", sa.Column("downstream_vertices", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove data_exchange table and exchange fields from transaction table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()
    dialect_name = conn.dialect.name

    # Drop data_exchange table if it exists
    if "data_exchange" in table_names:
        # Drop indexes first
        indexes = [idx["name"] for idx in inspector.get_indexes("data_exchange")]
        if "ix_data_exchange_transaction_id" in indexes:
            op.drop_index(op.f("ix_data_exchange_transaction_id"), table_name="data_exchange")
        if "ix_data_exchange_source_vertex_id" in indexes:
            op.drop_index(op.f("ix_data_exchange_source_vertex_id"), table_name="data_exchange")
        if "ix_data_exchange_target_vertex_id" in indexes:
            op.drop_index(op.f("ix_data_exchange_target_vertex_id"), table_name="data_exchange")
        if "ix_data_exchange_timestamp" in indexes:
            op.drop_index(op.f("ix_data_exchange_timestamp"), table_name="data_exchange")

        # Drop foreign key if it exists (PostgreSQL only)
        if dialect_name == "postgresql":
            foreign_keys = inspector.get_foreign_keys("data_exchange")
            if any(fk.get("name") == "fk_data_exchange_transaction_id" for fk in foreign_keys):
                op.drop_constraint("fk_data_exchange_transaction_id", "data_exchange", type_="foreignkey")

        # Drop table
        op.drop_table("data_exchange")

    # Remove exchange fields from transaction table if they exist
    if "transaction" in table_names:
        columns = {col["name"]: col for col in inspector.get_columns("transaction")}

        # Use batch mode for SQLite compatibility
        with op.batch_alter_table("transaction") as batch_op:
            if "downstream_vertices" in columns:
                batch_op.drop_column("downstream_vertices")
            if "exchange_count" in columns:
                batch_op.drop_column("exchange_count")
