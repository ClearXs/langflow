"""Document model for Holo knowledge system with pgvector support."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from pgvector.sqlalchemy import Vector
from pydantic import field_validator
from sqlalchemy import Column
from sqlmodel import JSON, DateTime, Field, SQLModel, Text, func


def utc_now():
    return datetime.now(timezone.utc)


class DocumentType(str, Enum):
    """Document types."""

    NOTE = "NOTE"  # BlockNote documents
    PDF = "PDF"
    WEBSITE = "WEBSITE"
    YOUTUBE = "YOUTUBE"
    NOTION = "NOTION"
    GITHUB = "GITHUB"
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    CONFLUENCE = "CONFLUENCE"
    LINEAR = "LINEAR"
    SLACK = "SLACK"
    JIRA = "JIRA"
    GMAIL = "GMAIL"
    GITLAB = "GITLAB"
    DROPBOX = "DROPBOX"
    ONEDRIVE = "ONEDRIVE"
    DISCORD = "DISCORD"
    EXTENSION = "EXTENSION"
    CRAWLED_URL = "CRAWLED_URL"
    YOUTUBE_VIDEO = "YOUTUBE_VIDEO"
    ELASTICSEARCH_CONNECTOR = "ELASTICSEARCH_CONNECTOR"
    BOOKSTACK_CONNECTOR = "BOOKSTACK_CONNECTOR"
    # Additional connector-specific document types
    AIRTABLE_CONNECTOR = "AIRTABLE_CONNECTOR"
    CLICKUP_CONNECTOR = "CLICKUP_CONNECTOR"
    CONFLUENCE_CONNECTOR = "CONFLUENCE_CONNECTOR"
    DISCORD_CONNECTOR = "DISCORD_CONNECTOR"
    GITHUB_CONNECTOR = "GITHUB_CONNECTOR"
    GOOGLE_CALENDAR_CONNECTOR = "GOOGLE_CALENDAR_CONNECTOR"
    GOOGLE_GMAIL_CONNECTOR = "GOOGLE_GMAIL_CONNECTOR"
    JIRA_CONNECTOR = "JIRA_CONNECTOR"
    LINEAR_CONNECTOR = "LINEAR_CONNECTOR"
    LUMA_CONNECTOR = "LUMA_CONNECTOR"
    NOTION_CONNECTOR = "NOTION_CONNECTOR"
    SLACK_CONNECTOR = "SLACK_CONNECTOR"
    WEBCRAWLER_CONNECTOR = "WEBCRAWLER_CONNECTOR"


class DocumentBase(SQLModel):
    """Base model for document."""

    title: str = Field(max_length=500, nullable=False)
    content: str = Field(sa_column=Column(Text, nullable=False))
    url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    doc_type: str = Field(max_length=50, nullable=False)
    blocknote_document: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    content_hash: str | None = Field(default=None, max_length=64, nullable=True, index=True)
    unique_identifier_hash: str = Field(max_length=64, nullable=False, unique=True, index=True)
    content_needs_reindexing: bool = Field(default=False, nullable=False)
    document_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
        description="Additional document metadata",
    )

    # File information
    file_name: str | None = Field(default=None, max_length=500, nullable=True)
    file_type: str | None = Field(
        default=None, max_length=50, nullable=True, description="File extension: pdf, docx, md, etc."
    )
    file_size: int | None = Field(default=None, nullable=True, description="File size in bytes")

    # data-construction integration
    data_construction_file_id: int | None = Field(
        default=None, nullable=True, index=True, description="File ID in data-construction service"
    )
    data_construction_folder_id: int | None = Field(
        default=None, nullable=True, index=True, description="Folder ID in data-construction service"
    )

    # Processing metadata
    etl_service: str | None = Field(
        default=None, max_length=50, nullable=True, description="ETL service used: unstructured, llamacloud, docling"
    )
    chunk_count: int = Field(default=0, nullable=False, description="Number of chunks generated")
    token_count: int = Field(default=0, nullable=False, description="Estimated token count")

    # Processing status
    processing_status: str = Field(
        default="pending", max_length=20, nullable=False, description="Status: pending, processing, completed, failed"
    )
    processing_error: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True), description="Error message if processing failed"
    )

    # Knowledge graph extraction
    graph_extracted: bool = Field(
        default=False, nullable=False, description="Whether knowledge graph has been extracted"
    )
    entity_count: int = Field(default=0, nullable=False, description="Number of entities extracted")
    relation_count: int = Field(default=0, nullable=False, description="Number of relations extracted")


class Document(DocumentBase, table=True):  # type: ignore[call-arg]
    """Document model with pgvector support for efficient vector operations."""

    __tablename__ = "documents"

    id: int = Field(default=None, primary_key=True)
    connector_id: int = Field(foreign_key="connectors.id", nullable=False, ondelete="CASCADE")
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="user.id", nullable=False)

    # Document-level embedding (pgvector on Postgres, JSON on SQLite)
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(3072).with_variant(JSON, "sqlite"), nullable=True),
    )

    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )
    indexed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When document was last indexed/vectorized",
    )


class DocumentCreate(SQLModel):
    """Model for creating a document."""

    connector_id: int
    space_id: int
    user_id: UUID
    title: str
    content: str
    url: str | None = None
    doc_type: str
    blocknote_document: dict | None = None
    embedding: list[float] | None = None
    content_hash: str | None = None
    unique_identifier_hash: str
    content_needs_reindexing: bool = False
    document_metadata: dict | None = None

    # New fields
    file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    data_construction_file_id: int | None = None
    data_construction_folder_id: int | None = None
    processing_status: str = "pending"
    graph_extracted: bool = False


class DocumentUpdate(SQLModel):
    """Model for updating a document."""

    title: str | None = None
    content: str | None = None
    url: str | None = None
    doc_type: str | None = None
    blocknote_document: dict | None = None
    embedding: list[float] | None = None
    content_hash: str | None = None
    content_needs_reindexing: bool | None = None
    document_metadata: dict | None = None

    # New fields
    file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    data_construction_file_id: int | None = None
    data_construction_folder_id: int | None = None
    etl_service: str | None = None
    chunk_count: int | None = None
    token_count: int | None = None
    processing_status: str | None = None
    processing_error: str | None = None
    graph_extracted: bool | None = None
    entity_count: int | None = None
    relation_count: int | None = None
    indexed_at: datetime | None = None


class DocumentRead(SQLModel):
    """Model for reading a document."""

    id: int
    connector_id: int
    space_id: int
    user_id: UUID
    title: str
    content: str
    url: str | None
    doc_type: str
    blocknote_document: dict | list | None  # Can be dict or list for compatibility
    embedding: list[float] | None
    content_hash: str | None
    unique_identifier_hash: str
    content_needs_reindexing: bool
    document_metadata: dict
    created_at: datetime
    updated_at: datetime | None

    # New fields
    file_name: str | None
    file_type: str | None
    file_size: int | None
    data_construction_file_id: int | None
    data_construction_folder_id: int | None
    etl_service: str | None
    chunk_count: int
    token_count: int
    processing_status: str
    processing_error: str | None
    graph_extracted: bool
    entity_count: int
    relation_count: int
    indexed_at: datetime | None

    @field_validator("blocknote_document", mode="before")
    @classmethod
    def parse_blocknote_document(cls, v):
        """Parse blocknote_document from JSON string if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    class Config:
        from_attributes = True
