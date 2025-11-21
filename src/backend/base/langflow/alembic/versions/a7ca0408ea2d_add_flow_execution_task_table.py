"""Add flow_execution_task table

Revision ID: a7ca0408ea2d
Revises: 71d43979e8bb
Create Date: 2025-11-20 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7ca0408ea2d"
down_revision: str | None = "71d43979e8bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add flow_execution_task table for tracking flow execution tasks."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()
    dialect_name = conn.dialect.name

    # Create flow_execution_task table if it doesn't exist
    if "flow_execution_task" not in table_names:
        # Determine UUID column types based on database dialect
        if dialect_name == "postgresql":
            uuid_type = sa.UUID()
        else:
            # SQLite: use TEXT for UUID compatibility
            uuid_type = sa.String()

        op.create_table(
            "flow_execution_task",
            sa.Column("id", uuid_type, nullable=False),
            sa.Column("run_id", sa.String(), nullable=False),
            sa.Column("flow_id", uuid_type, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("total_components", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_components", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_components", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_data_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_data_size_mb", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("total_exchanges", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_duration_ms", sa.Integer(), nullable=True),
            sa.Column("avg_memory_mb", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("user_id", uuid_type, nullable=True),
            sa.Column("trigger_type", sa.String(), nullable=False, server_default="'manual'"),
            sa.Column("first_error_component_id", sa.String(), nullable=True),
            sa.Column("first_error_message", sa.String(), nullable=True),
            sa.Column("execution_config", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_flow_execution_task"),
        )

        # Create indexes for better query performance
        op.create_index(
            op.f("ix_flow_execution_task_run_id"), "flow_execution_task", ["run_id"], unique=True
        )
        op.create_index(
            op.f("ix_flow_execution_task_flow_id"), "flow_execution_task", ["flow_id"], unique=False
        )
        op.create_index(
            op.f("ix_flow_execution_task_status"), "flow_execution_task", ["status"], unique=False
        )


def downgrade() -> None:
    """Remove flow_execution_task table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    if "flow_execution_task" in table_names:
        # Drop indexes first
        indexes = inspector.get_indexes("flow_execution_task")
        index_names = [idx["name"] for idx in indexes]

        if "ix_flow_execution_task_run_id" in index_names:
            op.drop_index(op.f("ix_flow_execution_task_run_id"), table_name="flow_execution_task")
        if "ix_flow_execution_task_flow_id" in index_names:
            op.drop_index(op.f("ix_flow_execution_task_flow_id"), table_name="flow_execution_task")
        if "ix_flow_execution_task_status" in index_names:
            op.drop_index(op.f("ix_flow_execution_task_status"), table_name="flow_execution_task")
        if "ix_flow_execution_task_created_at" in index_names:
            op.drop_index(op.f("ix_flow_execution_task_created_at"), table_name="flow_execution_task")

        # Drop the table
        op.drop_table("flow_execution_task")
