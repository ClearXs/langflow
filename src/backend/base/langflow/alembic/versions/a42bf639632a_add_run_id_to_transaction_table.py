"""add_run_id_to_transaction_table

Revision ID: a42bf639632a
Revises: a7ca0408ea2d
Create Date: 2025-11-20 14:50:10.465661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.engine.reflection import Inspector
from langflow.utils import migration


# revision identifiers, used by Alembic.
revision: str = 'a42bf639632a'
down_revision: Union[str, None] = 'a7ca0408ea2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # Check if run_id column already exists
    columns = [col['name'] for col in inspector.get_columns('transaction')]

    if 'run_id' not in columns:
        # Add run_id column to transaction table
        with op.batch_alter_table('transaction', schema=None) as batch_op:
            batch_op.add_column(sa.Column('run_id', sa.String(), nullable=True))

        # Create index for faster lookups
        op.create_index('ix_transaction_run_id', 'transaction', ['run_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()

    # Drop index first
    op.drop_index('ix_transaction_run_id', table_name='transaction')

    # Remove run_id column
    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.drop_column('run_id')
