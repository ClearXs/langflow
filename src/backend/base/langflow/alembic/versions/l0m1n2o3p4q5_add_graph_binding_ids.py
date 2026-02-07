"""add_graph_binding_ids

Revision ID: l0m1n2o3p4q5
Revises: k9l0m1n2o3p4
Create Date: 2026-02-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "l0m1n2o3p4q5"
down_revision: Union[str, None] = "k9l0m1n2o3p4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("entity", schema=None) as batch_op:
        batch_op.add_column(sa.Column("graph_node_id", sa.String(length=255), nullable=True))
        batch_op.create_index(batch_op.f("ix_entity_graph_node_id"), ["graph_node_id"], unique=False)

    with op.batch_alter_table("relation", schema=None) as batch_op:
        batch_op.add_column(sa.Column("graph_edge_id", sa.String(length=255), nullable=True))
        batch_op.create_index(batch_op.f("ix_relation_graph_edge_id"), ["graph_edge_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("relation", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_relation_graph_edge_id"))
        batch_op.drop_column("graph_edge_id")

    with op.batch_alter_table("entity", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_entity_graph_node_id"))
        batch_op.drop_column("graph_node_id")

