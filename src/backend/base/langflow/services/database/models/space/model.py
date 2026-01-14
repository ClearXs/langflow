"""Space model for Holo knowledge system."""

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import JSON, Column, DateTime, Field, SQLModel, Text, func


def utc_now():
    return datetime.now(timezone.utc)


class SpaceBase(SQLModel):
    """Base model for space."""

    name: str = Field(max_length=255, nullable=False)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    settings: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))
    agent_llm_id: int | None = Field(default=-1, nullable=True)
    document_summary_llm_id: int | None = Field(default=-2, nullable=True)
    citations_enabled: bool = Field(default=True, nullable=False, description="Enable citation support in responses")
    qna_custom_instructions: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True), description="Custom instructions for Q&A"
    )
    # Knowledge graph configuration fields
    enable_knowledge_graph: bool = Field(
        default=False, nullable=False, description="Enable knowledge graph features for this space"
    )
    auto_entity_extraction: bool = Field(
        default=True, nullable=False, description="Automatically extract entities from uploaded documents"
    )
    graph_llm_id: int | None = Field(default=None, nullable=True, description="LLM config for entity extraction")


class Space(SpaceBase, table=True):  # type: ignore[call-arg]
    """Space model for multi-tenant knowledge isolation."""

    __tablename__ = "spaces"

    id: int = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )


class SpaceCreate(SQLModel):
    """Model for creating a space."""

    name: str
    description: str | None = None
    settings: dict = Field(default_factory=dict)  # Fixed: default to empty dict instead of None
    agent_llm_id: int | None = -1
    document_summary_llm_id: int | None = -2
    citations_enabled: bool | None = True
    qna_custom_instructions: str | None = None
    enable_knowledge_graph: bool | None = False
    auto_entity_extraction: bool | None = True
    graph_llm_id: int | None = None


class SpaceUpdate(SQLModel):
    """Model for updating a space."""

    name: str | None = None
    description: str | None = None
    settings: dict | None = None
    agent_llm_id: int | None = None
    document_summary_llm_id: int | None = None
    citations_enabled: bool | None = None
    qna_custom_instructions: str | None = None
    enable_knowledge_graph: bool | None = None
    auto_entity_extraction: bool | None = None
    graph_llm_id: int | None = None


class SpaceRead(SQLModel):
    """Model for reading a space."""

    id: int
    user_id: UUID
    name: str
    description: str | None
    settings: dict
    agent_llm_id: int | None
    document_summary_llm_id: int | None
    citations_enabled: bool
    qna_custom_instructions: str | None
    enable_knowledge_graph: bool
    auto_entity_extraction: bool
    graph_llm_id: int | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
