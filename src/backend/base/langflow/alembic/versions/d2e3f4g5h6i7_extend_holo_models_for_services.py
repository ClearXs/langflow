"""extend_holo_models_for_services

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2025-12-30 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4g5h6i7'
down_revision: Union[str, None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Extend Holo models with service-required fields."""

    # 1. Extend User model with page limit tracking
    if not column_exists('user', 'pages_limit'):
        op.add_column('user', sa.Column('pages_limit', sa.Integer(), nullable=False, server_default='100'))

    if not column_exists('user', 'pages_used'):
        op.add_column('user', sa.Column('pages_used', sa.Integer(), nullable=False, server_default='0'))

    # 2. Extend Space model with citation and instruction support
    if not column_exists('spaces', 'citations_enabled'):
        op.add_column('spaces', sa.Column('citations_enabled', sa.Boolean(), nullable=False, server_default='1'))

    if not column_exists('spaces', 'qna_custom_instructions'):
        op.add_column('spaces', sa.Column('qna_custom_instructions', sa.Text(), nullable=True))

    # 3. Extend LLMConfig model with advanced configuration
    if not column_exists('llm_configs', 'custom_provider'):
        op.add_column('llm_configs', sa.Column('custom_provider', sa.String(length=100), nullable=True))

    if not column_exists('llm_configs', 'system_instructions'):
        op.add_column('llm_configs', sa.Column('system_instructions', sa.Text(), nullable=True))

    if not column_exists('llm_configs', 'use_default_system_instructions'):
        op.add_column('llm_configs', sa.Column('use_default_system_instructions', sa.Boolean(), nullable=False, server_default='1'))

    if not column_exists('llm_configs', 'citations_enabled'):
        op.add_column('llm_configs', sa.Column('citations_enabled', sa.Boolean(), nullable=False, server_default='1'))

    if not column_exists('llm_configs', 'litellm_params'):
        op.add_column('llm_configs', sa.Column('litellm_params', sa.JSON(), nullable=False, server_default='{}'))

    # 4. Extend Document model with metadata support
    if not column_exists('documents', 'document_metadata'):
        op.add_column('documents', sa.Column('document_metadata', sa.JSON(), nullable=False, server_default='{}'))


def downgrade() -> None:
    """Remove service-required field extensions."""

    # Remove in reverse order
    if column_exists('documents', 'document_metadata'):
        op.drop_column('documents', 'document_metadata')

    if column_exists('llm_configs', 'litellm_params'):
        op.drop_column('llm_configs', 'litellm_params')

    if column_exists('llm_configs', 'citations_enabled'):
        op.drop_column('llm_configs', 'citations_enabled')

    if column_exists('llm_configs', 'use_default_system_instructions'):
        op.drop_column('llm_configs', 'use_default_system_instructions')

    if column_exists('llm_configs', 'system_instructions'):
        op.drop_column('llm_configs', 'system_instructions')

    if column_exists('llm_configs', 'custom_provider'):
        op.drop_column('llm_configs', 'custom_provider')

    if column_exists('spaces', 'qna_custom_instructions'):
        op.drop_column('spaces', 'qna_custom_instructions')

    if column_exists('spaces', 'citations_enabled'):
        op.drop_column('spaces', 'citations_enabled')

    if column_exists('user', 'pages_used'):
        op.drop_column('user', 'pages_used')

    if column_exists('user', 'pages_limit'):
        op.drop_column('user', 'pages_limit')
