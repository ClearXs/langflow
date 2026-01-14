"""Entity model for knowledge graph."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langflow.services.database.models.relation.model import Relation
    from langflow.services.database.models.space.model import Space
    from langflow.services.database.models.document.model import Document
    from langflow.services.database.models.chunk.model import Chunk


class Entity(SQLModel, table=True):
    """Entity model - Knowledge entities extracted from documents.

    Entities represent key concepts, people, organizations, locations, etc.
    extracted from documents using LLM or NER models.
    """

    __tablename__ = "entity"

    # Primary key
    id: int | None = Field(default=None, primary_key=True)

    # Foreign keys
    space_id: int = Field(foreign_key="spaces.id", index=True, ondelete="CASCADE")
    document_id: int | None = Field(default=None, foreign_key="documents.id", index=True, ondelete="CASCADE")
    chunk_id: int | None = Field(default=None, foreign_key="chunks.id", index=True, ondelete="CASCADE")

    # Entity attributes
    name: str = Field(index=True, max_length=500, description="Entity name")
    entity_type: str = Field(
        index=True,
        max_length=100,
        description="Entity type (Person, Organization, Location, Concept, etc.)",
    )
    description: str | None = Field(default=None, max_length=2000, description="Entity description")
    aliases: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Alternative names or acronyms",
    )

    # Vector embedding for entity retrieval
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Vector embedding for semantic search",
    )

    # Additional properties
    properties: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional custom properties",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    # Relationships
    # Note: Relationships are defined but not used in queries to avoid circular imports
    # Use CRUD operations instead

    class Config:
        arbitrary_types_allowed = True
