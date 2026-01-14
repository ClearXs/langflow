"""Chunk model for Holo knowledge system (without pgvector)."""

from datetime import datetime, timezone

from sqlalchemy import Column
from sqlmodel import JSON, DateTime, Field, SQLModel, Text, func


def utc_now():
    return datetime.now(timezone.utc)


class ChunkBase(SQLModel):
    """Base model for chunk."""

    content: str = Field(sa_column=Column(Text, nullable=False))
    chunk_index: int = Field(nullable=False)
    chunk_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))


class Chunk(ChunkBase, table=True):  # type: ignore[call-arg]
    """Chunk model (embedding stored as JSON array instead of pgvector)."""

    __tablename__ = "chunks"

    id: int = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="documents.id", nullable=False, ondelete="CASCADE")
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    embedding: list[float] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
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

    class Config:
        from_attributes = True
