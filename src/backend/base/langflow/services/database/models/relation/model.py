"""Relation model for knowledge graph."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langflow.services.database.models.entity.model import Entity
    from langflow.services.database.models.space.model import Space
    from langflow.services.database.models.document.model import Document
    from langflow.services.database.models.chunk.model import Chunk


class Relation(SQLModel, table=True):
    """Relation model - Relationships between entities in the knowledge graph.

    Relations represent connections between entities, such as:
    - PartOf (hierarchy)
    - LeadsTo (causation)
    - RelatedTo (association)
    - CreatedBy (authorship)
    etc.
    """

    __tablename__ = "relation"

    # Primary key
    id: int | None = Field(default=None, primary_key=True)

    # Foreign keys
    space_id: int = Field(foreign_key="spaces.id", index=True, ondelete="CASCADE")
    source_entity_id: int = Field(foreign_key="entity.id", index=True, description="Source entity ID", ondelete="CASCADE")
    target_entity_id: int = Field(foreign_key="entity.id", index=True, description="Target entity ID", ondelete="CASCADE")
    document_id: int | None = Field(default=None, foreign_key="documents.id", index=True, ondelete="CASCADE")
    chunk_id: int | None = Field(default=None, foreign_key="chunks.id", index=True, ondelete="CASCADE")

    # Relation attributes
    relation_type: str = Field(
        index=True,
        max_length=100,
        description="Relationship type (PartOf, LeadsTo, RelatedTo, etc.)",
    )
    description: str | None = Field(default=None, max_length=2000, description="Relationship description")
    weight: float = Field(default=1.0, description="Relationship weight/confidence score (0.0-1.0)")

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
