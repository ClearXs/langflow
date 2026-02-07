"""update_vector_dimension_to_3072

Revision ID: k9l0m1n2o3p4
Revises: j8k9l0m1n2o3
Create Date: 2026-01-30 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'k9l0m1n2o3p4'
down_revision: Union[str, None] = 'j8k9l0m1n2o3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update vector dimensions from 1536 to 3072 for text-embedding-3-large.

    Note: For SQLite, this migration is a no-op since SQLite stores embeddings as BLOB/JSON
    and doesn't have native vector type constraints. The dimension validation happens
    in the application layer via the Vector field definition in the models.

    For PostgreSQL with pgvector, this updates the vector column type.
    """
    # Check if we're using PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # For PostgreSQL with pgvector
        op.execute("""
            -- Update documents table vector dimension
            ALTER TABLE documents
            ALTER COLUMN embedding TYPE vector(3072);

            -- Update chunks table vector dimension
            ALTER TABLE chunks
            ALTER COLUMN embedding TYPE vector(3072);

            -- Recreate indexes for new dimension
            DROP INDEX IF EXISTS idx_documents_embedding_vector;
            DROP INDEX IF EXISTS idx_chunks_embedding_vector;

            CREATE INDEX idx_documents_embedding_vector ON documents
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);

            CREATE INDEX idx_chunks_embedding_vector ON chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 1000);
        """)
    else:
        # For SQLite, no schema changes needed
        # Embeddings are stored as BLOB/JSON and dimension is validated in Python code
        pass


def downgrade() -> None:
    """Revert vector dimensions from 3072 to 1536."""
    # Check if we're using PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # For PostgreSQL with pgvector
        op.execute("""
            -- Drop new indexes
            DROP INDEX IF EXISTS idx_documents_embedding_vector;
            DROP INDEX IF EXISTS idx_chunks_embedding_vector;

            -- Revert documents table vector dimension
            ALTER TABLE documents
            ALTER COLUMN embedding TYPE vector(1536);

            -- Revert chunks table vector dimension
            ALTER TABLE chunks
            ALTER COLUMN embedding TYPE vector(1536);

            -- Recreate original indexes
            CREATE INDEX idx_documents_embedding_vector ON documents
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);

            CREATE INDEX idx_chunks_embedding_vector ON chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 1000);
        """)
    else:
        # For SQLite, no schema changes needed
        pass
