"""Entity Pydantic schemas for API validation."""

from datetime import datetime
from pydantic import BaseModel, Field


class EntityCreate(BaseModel):
    """Schema for creating a new entity."""

    space_id: int
    document_id: int | None = None
    chunk_id: int | None = None
    name: str = Field(..., max_length=500)
    entity_type: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=2000)
    aliases: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    properties: dict = Field(default_factory=dict)


class EntityRead(BaseModel):
    """Schema for reading an entity."""

    id: int
    space_id: int
    document_id: int | None
    chunk_id: int | None
    name: str
    entity_type: str
    description: str | None
    aliases: list[str]
    embedding: list[float] | None
    properties: dict
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class EntityUpdate(BaseModel):
    """Schema for updating an entity."""

    name: str | None = Field(None, max_length=500)
    entity_type: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=2000)
    aliases: list[str] | None = None
    embedding: list[float] | None = None
    properties: dict | None = None
