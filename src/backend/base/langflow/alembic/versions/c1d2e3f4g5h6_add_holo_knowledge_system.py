"""add_holo_knowledge_system

Revision ID: c1d2e3f4g5h6
Revises: a42bf639632a
Create Date: 2025-12-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import sqlite
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, None] = 'a42bf639632a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add all Holo knowledge system tables."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. Create spaces table
    if 'spaces' not in existing_tables:
        op.create_table(
            'spaces',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('agent_llm_id', sa.Integer(), nullable=True),
            sa.Column('document_summary_llm_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # 2. Create connectors table
    if 'connectors' not in existing_tables:
        op.create_table(
            'connectors',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column('connector_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
            sa.Column('is_enabled', sa.Boolean(), nullable=False),
            sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # 3. Create documents table
    if 'documents' not in existing_tables:
        op.create_table(
            'documents',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('connector_id', sa.Integer(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('url', sa.Text(), nullable=True),
            sa.Column('doc_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
            sa.Column('blocknote_document', sa.JSON(), nullable=True),
            sa.Column('content_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
            sa.Column('unique_identifier_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
            sa.Column('content_needs_reindexing', sa.Boolean(), nullable=False),
            sa.Column('embedding', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('unique_identifier_hash')
        )
        op.create_index('ix_documents_content_hash', 'documents', ['content_hash'])
        op.create_index('ix_documents_unique_identifier_hash', 'documents', ['unique_identifier_hash'])

    # 4. Create chunks table
    if 'chunks' not in existing_tables:
        op.create_table(
            'chunks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('chunk_index', sa.Integer(), nullable=False),
            sa.Column('chunk_metadata', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('embedding', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 5. Create roles table
    if 'roles' not in existing_tables:
        op.create_table(
            'roles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('search_space_id', sa.Integer(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
            sa.Column('description', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
            sa.Column('is_custom', sa.Boolean(), nullable=False),
            sa.Column('permissions', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 6. Create space_memberships table
    if 'space_memberships' not in existing_tables:
        op.create_table(
            'space_memberships',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('role_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 7. Create space_invites table
    if 'space_invites' not in existing_tables:
        op.create_table(
            'space_invites',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('space_id', sa.Integer(), nullable=False),
            sa.Column('role_id', sa.Integer(), nullable=False),
            sa.Column('inviter_id', sa.String(), nullable=False),
            sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column('token', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('is_used', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['inviter_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token')
        )
        op.create_index('ix_space_invites_token', 'space_invites', ['token'])

    # 8. Create llm_configs table
    if 'llm_configs' not in existing_tables:
        op.create_table(
            'llm_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('search_space_id', sa.Integer(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
            sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column('api_base', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
            sa.Column('api_key', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
            sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 9. Create logs table
    if 'logs' not in existing_tables:
        op.create_table(
            'logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('search_space_id', sa.Integer(), nullable=False),
            sa.Column('level', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
            sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('source', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
            sa.Column('log_metadata', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 10. Create podcasts table
    if 'podcasts' not in existing_tables:
        op.create_table(
            'podcasts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('search_space_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
            sa.Column('podcast_transcript', sa.JSON(), nullable=True),
            sa.Column('file_location', sa.Text(), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['search_space_id'], ['spaces.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    """Remove all Holo knowledge system tables."""
    # Drop tables in reverse order to respect foreign key constraints
    op.drop_table('podcasts')
    op.drop_table('logs')
    op.drop_table('llm_configs')
    op.drop_index('ix_space_invites_token', table_name='space_invites')
    op.drop_table('space_invites')
    op.drop_table('space_memberships')
    op.drop_table('roles')
    op.drop_table('chunks')
    op.drop_index('ix_documents_unique_identifier_hash', table_name='documents')
    op.drop_index('ix_documents_content_hash', table_name='documents')
    op.drop_table('documents')
    op.drop_table('connectors')
    op.drop_table('spaces')
