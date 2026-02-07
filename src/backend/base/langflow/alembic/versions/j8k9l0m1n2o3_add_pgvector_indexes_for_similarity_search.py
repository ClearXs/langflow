"""add_pgvector_indexes_for_similarity_search

Revision ID: j8k9l0m1n2o3
Revises: bc8d5b8da775
Create Date: 2026-01-28 00:00:00.000000

This migration adds optimized indexes for vector similarity search:
1. HNSW index on chunks.embedding for fast cosine similarity search
2. HNSW index on documents.embedding for document-level similarity
3. GIN index on chunks.tsvector for full-text search
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'j8k9l0m1n2o3'
down_revision: Union[str, None] = 'bc8d5b8da775'  # Fixed: should come after bc8d5b8da775
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pgvector HNSW and GIN indexes for optimized retrieval."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    # Only apply for PostgreSQL
    if dialect_name == 'postgresql':
        # 1. Create HNSW index for chunk embeddings (cosine distance)
        # HNSW parameters:
        #   m = 16: Number of connections per layer (default is 16, trade-off between index size and search quality)
        #   ef_construction = 64: Controls index construction quality (higher = better quality but slower build)
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_embedding_hnsw
            ON chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

        # 2. Create HNSW index for document embeddings
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_document_embedding_hnsw
            ON documents
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

        # 3. Create GIN index for full-text search on chunks
        # This enables fast full-text search using PostgreSQL's tsvector
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_tsvector_gin
            ON chunks
            USING gin (tsvector);
        """)

        # 4. Add index on document_id in chunks for fast joins
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_document_id
            ON chunks (document_id);
        """)

        # 5. Add index on space_id in chunks for filtering by space
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_space_id
            ON chunks (space_id);
        """)


def downgrade() -> None:
    """Remove pgvector indexes."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == 'postgresql':
        op.execute("DROP INDEX IF EXISTS idx_chunk_space_id;")
        op.execute("DROP INDEX IF EXISTS idx_chunk_document_id;")
        op.execute("DROP INDEX IF EXISTS idx_chunk_tsvector_gin;")
        op.execute("DROP INDEX IF EXISTS idx_document_embedding_hnsw;")
        op.execute("DROP INDEX IF EXISTS idx_chunk_embedding_hnsw;")
