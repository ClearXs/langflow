"""Relation Pydantic schemas for API validation."""

from datetime import datetime

from pydantic import BaseModel, Field


class RelationCreate(BaseModel):
    """Schema for creating a new relation."""

    space_id: int
    source_entity_id: int
    target_entity_id: int
    document_id: int | None = None
    chunk_id: int | None = None
    relation_type: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=2000)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict = Field(default_factory=dict)
    graph_edge_id: str | None = Field(default=None, max_length=255)


class RelationRead(BaseModel):
    """Schema for reading a relation."""

    id: int
    space_id: int
    source_entity_id: int
    target_entity_id: int
    document_id: int | None
    chunk_id: int | None
    relation_type: str
    description: str | None
    weight: float
    properties: dict
    graph_edge_id: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class RelationUpdate(BaseModel):
    """Schema for updating a relation."""

    relation_type: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=2000)
    weight: float | None = Field(None, ge=0.0, le=1.0)
    properties: dict | None = None
    graph_edge_id: str | None = Field(default=None, max_length=255)
