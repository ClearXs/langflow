"""Chunk model for Holo knowledge system with pgvector and full-text search support."""

from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text as SQLText
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlmodel import JSON, DateTime, Field, SQLModel, Text, func


def utc_now():
    return datetime.now(timezone.utc)


class ChunkBase(SQLModel):
    """Base model for chunk."""

    content: str = Field(sa_column=Column(Text, nullable=False))
    chunk_index: int = Field(nullable=False, description="Position of chunk in the document")
    chunk_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))

    # Chunk metadata
    token_count: int = Field(default=0, nullable=False, description="Estimated token count for this chunk")
    chunk_type: str = Field(default="text", max_length=20, nullable=False, description="Chunk type: text, code, table")

    # Code-specific metadata (when chunk_type='code')
    programming_language: str | None = Field(
        default=None, max_length=50, nullable=True, description="Programming language for code chunks"
    )


class Chunk(ChunkBase, table=True):  # type: ignore[call-arg]
    """Chunk model with pgvector for embeddings and tsvector for full-text search."""

    __tablename__ = "chunks"

    id: int = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="documents.id", nullable=False, ondelete="CASCADE")
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")

    # Chunk-level embedding (pgvector on Postgres, JSON on SQLite)
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(3072).with_variant(JSON, "sqlite"), nullable=True),
    )

    # Full-text search vector (PostgreSQL: TSVECTOR, SQLite: Text)
    # Automatically updated by trigger on PostgreSQL, manually managed on SQLite
    tsvector: str | None = Field(
        default=None, sa_column=Column(TSVECTOR().with_variant(SQLText(), "sqlite"), nullable=True)
    )

    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class ChunkCreate(SQLModel):
    """Model for creating a chunk."""

    document_id: int
    space_id: int
    content: str
    chunk_index: int
    chunk_metadata: dict | None = None
    embedding: list[float] | None = None

    # New fields
    token_count: int = 0
    chunk_type: str = "text"
    programming_language: str | None = None


class ChunkRead(SQLModel):
    """Model for reading a chunk."""

    id: int
    document_id: int
    space_id: int
    content: str
    chunk_index: int
    chunk_metadata: dict
    embedding: list[float] | None
    created_at: datetime

    # New fields
    token_count: int
    chunk_type: str
    programming_language: str | None

    class Config:
        from_attributes = True
