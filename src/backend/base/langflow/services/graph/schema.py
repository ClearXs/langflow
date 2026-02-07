"""Pydantic schemas for graph API responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GraphNodeRead(BaseModel):
    id: str
    name: str | None = None
    entity_type: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    space_id: int | None = None
    document_id: int | None = None
    chunk_id: int | None = None
    document_title: str | None = None  # Title of the source document


class GraphEdgeRead(BaseModel):
    id: str
    source: str
    target: str
    relation_type: str
    description: str | None = None
    weight: float | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    nodes: list[GraphNodeRead]
    edges: list[GraphEdgeRead]
    raw_paths: list[dict[str, Any]]
