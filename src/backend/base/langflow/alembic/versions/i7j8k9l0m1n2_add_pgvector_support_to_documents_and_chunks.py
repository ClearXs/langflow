"""add_pgvector_support_to_documents_and_chunks

Revision ID: i7j8k9l0m1n2
Revises: h6i7j8k9l0m1
Create Date: 2026-01-23 00:00:00.000000

This migration adds:
1. pgvector extension for efficient vector operations
2. Converts document and chunk embeddings from JSON to vector type
3. Adds HNSW indexes for fast similarity search
4. Adds tsvector column and GIN index for full-text search
5. Adds new fields for data-construction integration and processing status
6. Adds connector data_construction_folder_id and indexing status fields
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'i7j8k9l0m1n2'
down_revision: Union[str, None] = 'h6i7j8k9l0m1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to pgvector-based document and chunk storage."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    # Only apply pgvector changes for PostgreSQL
    if dialect_name == 'postgresql':
        # 1. Enable pgvector extension
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

        # 2. Add new columns to documents table
        op.add_column('documents', sa.Column('file_name', sa.String(length=500), nullable=True))
        op.add_column('documents', sa.Column('file_type', sa.String(length=50), nullable=True))
        op.add_column('documents', sa.Column('file_size', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('data_construction_file_id', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('data_construction_folder_id', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('etl_service', sa.String(length=50), nullable=True))
        op.add_column('documents', sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='pending'))
        op.add_column('documents', sa.Column('processing_error', sa.Text(), nullable=True))
        op.add_column('documents', sa.Column('graph_extracted', sa.Boolean(), nullable=False, server_default='false'))
        op.add_column('documents', sa.Column('entity_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('relation_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True))

        # 3. Convert document embeddings from JSON to vector
        # Create temporary column for migration
        op.execute("ALTER TABLE documents ADD COLUMN embedding_vector vector(1536)")

        # Migrate existing data (if any)
        op.execute("""
            UPDATE documents
            SET embedding_vector = embedding::text::vector(1536)
            WHERE embedding IS NOT NULL AND jsonb_array_length(embedding::jsonb) = 1536
        """)

        # Drop old column and rename new one
        op.drop_column('documents', 'embedding')
        op.execute("ALTER TABLE documents RENAME COLUMN embedding_vector TO embedding")

        # 4. Add indexes for documents
        op.create_index('idx_document_data_construction_file_id', 'documents', ['data_construction_file_id'])
        op.create_index('idx_document_data_construction_folder_id', 'documents', ['data_construction_folder_id'])
        op.create_index('idx_document_processing_status', 'documents', ['processing_status'])

        # Create HNSW index for document embeddings (for similarity search)
        op.execute("""
            CREATE INDEX idx_document_embedding ON documents
            USING hnsw (embedding vector_cosine_ops)
        """)

        # 5. Add new columns to chunks table
        op.add_column('chunks', sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('chunks', sa.Column('chunk_type', sa.String(length=20), nullable=False, server_default='text'))
        op.add_column('chunks', sa.Column('programming_language', sa.String(length=50), nullable=True))

        # Add tsvector column for full-text search
        op.add_column('chunks', sa.Column('tsvector', postgresql.TSVECTOR(), nullable=True))

        # 6. Convert chunk embeddings from JSON to vector
        # Create temporary column for migration
        op.execute("ALTER TABLE chunks ADD COLUMN embedding_vector vector(1536)")

        # Migrate existing data (if any)
        op.execute("""
            UPDATE chunks
            SET embedding_vector = embedding::text::vector(1536)
            WHERE embedding IS NOT NULL AND jsonb_array_length(embedding::jsonb) = 1536
        """)

        # Drop old column and rename new one
        op.drop_column('chunks', 'embedding')
        op.execute("ALTER TABLE chunks RENAME COLUMN embedding_vector TO embedding")

        # 7. Create HNSW index for chunk embeddings (for similarity search)
        op.execute("""
            CREATE INDEX idx_chunk_embedding ON chunks
            USING hnsw (embedding vector_cosine_ops)
        """)

        # 8. Create GIN index for full-text search
        op.create_index('idx_chunk_tsvector', 'chunks', ['tsvector'], postgresql_using='gin')

        # 9. Create trigger to automatically update tsvector on insert/update
        op.execute("""
            CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE
            ON chunks FOR EACH ROW EXECUTE FUNCTION
            tsvector_update_trigger(tsvector, 'pg_catalog.english', content)
        """)

        # 10. Update existing rows to populate tsvector
        op.execute("""
            UPDATE chunks
            SET tsvector = to_tsvector('english', content)
            WHERE tsvector IS NULL
        """)

        # 11. Add connector fields for data-construction integration
        op.add_column('connectors', sa.Column('data_construction_folder_id', sa.Integer(), nullable=True))
        op.add_column('connectors', sa.Column('indexing_status', sa.String(length=20), nullable=False, server_default='idle'))
        op.add_column('connectors', sa.Column('indexed_file_count', sa.Integer(), nullable=False, server_default='0'))

        # Create index for connector folder ID
        op.create_index('idx_connector_data_construction_folder_id', 'connectors', ['data_construction_folder_id'])

    else:
        # For SQLite (development), just add columns without vector support
        # Keep embeddings as JSON for compatibility
        op.add_column('documents', sa.Column('file_name', sa.String(length=500), nullable=True))
        op.add_column('documents', sa.Column('file_type', sa.String(length=50), nullable=True))
        op.add_column('documents', sa.Column('file_size', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('data_construction_file_id', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('data_construction_folder_id', sa.Integer(), nullable=True))
        op.add_column('documents', sa.Column('etl_service', sa.String(length=50), nullable=True))
        op.add_column('documents', sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='pending'))
        op.add_column('documents', sa.Column('processing_error', sa.Text(), nullable=True))
        op.add_column('documents', sa.Column('graph_extracted', sa.Boolean(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('entity_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('relation_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('documents', sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True))

        op.add_column('chunks', sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'))
        op.add_column('chunks', sa.Column('chunk_type', sa.String(length=20), nullable=False, server_default='text'))
        op.add_column('chunks', sa.Column('programming_language', sa.String(length=50), nullable=True))

        # Create indexes for SQLite
        op.create_index('idx_document_data_construction_file_id', 'documents', ['data_construction_file_id'])
        op.create_index('idx_document_data_construction_folder_id', 'documents', ['data_construction_folder_id'])
        op.create_index('idx_document_processing_status', 'documents', ['processing_status'])

        # Add connector fields for SQLite
        op.add_column('connectors', sa.Column('data_construction_folder_id', sa.Integer(), nullable=True))
        op.add_column('connectors', sa.Column('indexing_status', sa.String(length=20), nullable=False, server_default='idle'))
        op.add_column('connectors', sa.Column('indexed_file_count', sa.Integer(), nullable=False, server_default='0'))
        op.create_index('idx_connector_data_construction_folder_id', 'connectors', ['data_construction_folder_id'])


def downgrade() -> None:
    """Downgrade from pgvector back to JSON embeddings."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == 'postgresql':
        # 1. Drop trigger
        op.execute("DROP TRIGGER IF EXISTS tsvector_update ON chunks")

        # 2. Drop indexes
        op.drop_index('idx_chunk_tsvector', table_name='chunks')
        op.execute("DROP INDEX IF EXISTS idx_chunk_embedding")
        op.execute("DROP INDEX IF EXISTS idx_document_embedding")
        op.drop_index('idx_document_processing_status', table_name='documents')
        op.drop_index('idx_document_data_construction_folder_id', table_name='documents')
        op.drop_index('idx_document_data_construction_file_id', table_name='documents')

        # 3. Convert chunks back to JSON
        op.execute("ALTER TABLE chunks ADD COLUMN embedding_json JSON")
        op.execute("""
            UPDATE chunks
            SET embedding_json = array_to_json(embedding::real[])::json
            WHERE embedding IS NOT NULL
        """)
        op.drop_column('chunks', 'embedding')
        op.execute("ALTER TABLE chunks RENAME COLUMN embedding_json TO embedding")

        # 4. Remove new chunk columns
        op.drop_column('chunks', 'tsvector')
        op.drop_column('chunks', 'programming_language')
        op.drop_column('chunks', 'chunk_type')
        op.drop_column('chunks', 'token_count')

        # 5. Convert documents back to JSON
        op.execute("ALTER TABLE documents ADD COLUMN embedding_json JSON")
        op.execute("""
            UPDATE documents
            SET embedding_json = array_to_json(embedding::real[])::json
            WHERE embedding IS NOT NULL
        """)
        op.drop_column('documents', 'embedding')
        op.execute("ALTER TABLE documents RENAME COLUMN embedding_json TO embedding")

        # 6. Remove new document columns
        op.drop_column('documents', 'indexed_at')
        op.drop_column('documents', 'relation_count')
        op.drop_column('documents', 'entity_count')
        op.drop_column('documents', 'graph_extracted')
        op.drop_column('documents', 'processing_error')
        op.drop_column('documents', 'processing_status')
        op.drop_column('documents', 'token_count')
        op.drop_column('documents', 'chunk_count')
        op.drop_column('documents', 'etl_service')
        op.drop_column('documents', 'data_construction_folder_id')
        op.drop_column('documents', 'data_construction_file_id')
        op.drop_column('documents', 'file_size')
        op.drop_column('documents', 'file_type')
        op.drop_column('documents', 'file_name')

        # 7. Remove connector columns
        op.drop_index('idx_connector_data_construction_folder_id', table_name='connectors')
        op.drop_column('connectors', 'indexed_file_count')
        op.drop_column('connectors', 'indexing_status')
        op.drop_column('connectors', 'data_construction_folder_id')

    else:
        # SQLite downgrade
        op.drop_index('idx_document_processing_status', table_name='documents')
        op.drop_index('idx_document_data_construction_folder_id', table_name='documents')
        op.drop_index('idx_document_data_construction_file_id', table_name='documents')

        op.drop_column('chunks', 'programming_language')
        op.drop_column('chunks', 'chunk_type')
        op.drop_column('chunks', 'token_count')

        op.drop_column('documents', 'indexed_at')
        op.drop_column('documents', 'relation_count')
        op.drop_column('documents', 'entity_count')
        op.drop_column('documents', 'graph_extracted')
        op.drop_column('documents', 'processing_error')
        op.drop_column('documents', 'processing_status')
        op.drop_column('documents', 'token_count')
        op.drop_column('documents', 'chunk_count')
        op.drop_column('documents', 'etl_service')
        op.drop_column('documents', 'data_construction_folder_id')
        op.drop_column('documents', 'data_construction_file_id')
        op.drop_column('documents', 'file_size')
        op.drop_column('documents', 'file_type')
        op.drop_column('documents', 'file_name')

        # Remove connector columns
        op.drop_index('idx_connector_data_construction_folder_id', table_name='connectors')
        op.drop_column('connectors', 'indexed_file_count')
        op.drop_column('connectors', 'indexing_status')
        op.drop_column('connectors', 'data_construction_folder_id')
