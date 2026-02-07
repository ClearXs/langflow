"""Entity model for knowledge graph."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


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

    # Additional properties
    properties: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional custom properties",
    )

    # Graph binding (Neo4j)
    graph_node_id: str | None = Field(
        default=None,
        index=True,
        max_length=255,
        description="Neo4j graph node ID",
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
