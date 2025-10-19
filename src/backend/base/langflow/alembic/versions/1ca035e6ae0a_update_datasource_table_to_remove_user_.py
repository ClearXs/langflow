"""Update datasource table to remove user relationship and use plain password

Revision ID: 1ca035e6ae0a
Revises: 5f7a3b2c8d9e
Create Date: 2025-10-16 20:40:50.134611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.engine.reflection import Inspector
from langflow.utils import migration


# revision identifiers, used by Alembic.
revision: str = '1ca035e6ae0a'
down_revision: Union[str, None] = '5f7a3b2c8d9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update datasource table to remove user relationship and use plain password."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only update table if it exists
    if "datasource" in table_names:
        # Check if table has old schema
        columns = {col['name']: col for col in inspector.get_columns('datasource')}

        # Add password column if it doesn't exist
        if 'password' not in columns and 'encrypted_password' in columns:
            # First, copy data from encrypted_password to password
            # Note: In SQLite we can't directly rename, so we add new column
            op.add_column('datasource', sa.Column('password', sa.String(), nullable=True))

            # Copy data from encrypted_password to password (they're the same for now)
            op.execute("UPDATE datasource SET password = encrypted_password")

            # Make password non-nullable
            with op.batch_alter_table('datasource') as batch_op:
                batch_op.alter_column('password', nullable=False)

            # Drop encrypted_password column
            with op.batch_alter_table('datasource') as batch_op:
                batch_op.drop_column('encrypted_password')

        # Drop user_id index if it exists
        indexes = inspector.get_indexes('datasource')
        if any(idx['name'] == 'ix_datasource_user_id' for idx in indexes):
            op.drop_index('ix_datasource_user_id', table_name='datasource')

        # Drop foreign key constraint if it exists (SQLite doesn't support dropping FK directly)
        # We need to recreate the table without FK
        foreign_keys = inspector.get_foreign_keys('datasource')
        if any(fk.get('referred_table') == 'user' for fk in foreign_keys):
            # For SQLite, we need to use batch mode to drop FK
            with op.batch_alter_table('datasource') as batch_op:
                batch_op.drop_column('user_id')


def downgrade() -> None:
    """Revert datasource table to use encrypted_password and user relationship."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    table_names = inspector.get_table_names()

    # Only update table if it exists
    if "datasource" in table_names:
        columns = {col['name']: col for col in inspector.get_columns('datasource')}

        # Add back user_id column
        if 'user_id' not in columns:
            op.add_column('datasource', sa.Column('user_id', sa.String(length=32), nullable=True))
            op.create_index('ix_datasource_user_id', 'datasource', ['user_id'], unique=False)

        # Rename password back to encrypted_password
        if 'password' in columns and 'encrypted_password' not in columns:
            op.add_column('datasource', sa.Column('encrypted_password', sa.String(), nullable=True))
            op.execute("UPDATE datasource SET encrypted_password = password")

            with op.batch_alter_table('datasource') as batch_op:
                batch_op.alter_column('encrypted_password', nullable=False)
                batch_op.drop_column('password')
