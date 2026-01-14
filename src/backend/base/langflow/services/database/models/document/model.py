"""Document model for Holo knowledge system (without pgvector)."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy import Column
from sqlmodel import JSON, DateTime, Field, SQLModel, Text, func


def utc_now():
    return datetime.now(timezone.utc)


class DocumentType(str, Enum):
    """Document types."""

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
    document_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"), description="Additional document metadata")


class Document(DocumentBase, table=True):  # type: ignore[call-arg]
    """Document model (embedding stored as JSON array instead of pgvector)."""

    __tablename__ = "documents"

    id: int = Field(default=None, primary_key=True)
    connector_id: int = Field(foreign_key="connectors.id", nullable=False, ondelete="CASCADE")
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    embedding: list[float] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
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
    blocknote_document: dict | None
    embedding: list[float] | None
    content_hash: str | None
    unique_identifier_hash: str
    content_needs_reindexing: bool
    document_metadata: dict
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
