"""Connector model for Holo knowledge system."""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlmodel import JSON, Column, DateTime, Field, SQLModel, func


def utc_now():
    return datetime.now(timezone.utc)


class ConnectorType(str, Enum):
    """Connector types."""

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
    # Additional connector types from SurfSense
    CLICKUP = "CLICKUP"
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    AIRTABLE = "AIRTABLE"
    LUMA = "LUMA"
    ELASTICSEARCH = "ELASTICSEARCH"
    WEBCRAWLER = "WEBCRAWLER"
    BOOKSTACK = "BOOKSTACK"
    # Connector type aliases with _CONNECTOR suffix for backward compatibility
    SLACK_CONNECTOR = "SLACK"
    NOTION_CONNECTOR = "NOTION"
    GITHUB_CONNECTOR = "GITHUB"
    LINEAR_CONNECTOR = "LINEAR"
    JIRA_CONNECTOR = "JIRA"
    CONFLUENCE_CONNECTOR = "CONFLUENCE"
    BOOKSTACK_CONNECTOR = "BOOKSTACK"
    CLICKUP_CONNECTOR = "CLICKUP"
    GOOGLE_CALENDAR_CONNECTOR = "GOOGLE_CALENDAR"
    AIRTABLE_CONNECTOR = "AIRTABLE"
    GOOGLE_GMAIL_CONNECTOR = "GOOGLE_GMAIL"
    DISCORD_CONNECTOR = "DISCORD"
    LUMA_CONNECTOR = "LUMA"
    ELASTICSEARCH_CONNECTOR = "ELASTICSEARCH"
    WEBCRAWLER_CONNECTOR = "WEBCRAWLER"


class ConnectorBase(SQLModel):
    """Base model for connector."""

    name: str = Field(max_length=255, nullable=False)
    connector_type: str = Field(max_length=50, nullable=False)
    is_enabled: bool = Field(default=True, nullable=False)
    config: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))

    # data-construction integration
    data_construction_folder_id: int | None = Field(default=None, nullable=True, description="Folder ID in data-construction service for this connector")

    # Periodic indexing fields
    periodic_indexing_enabled: bool = Field(default=False, nullable=False)
    indexing_frequency_minutes: int | None = Field(default=None, nullable=True)
    next_scheduled_at: datetime | None = Field(default=None, nullable=True)
    is_indexable: bool = Field(default=True, nullable=False)
    last_indexed_at: datetime | None = Field(default=None, nullable=True)

    # Indexing status and statistics
    indexing_status: str = Field(default="idle", max_length=20, nullable=False, description="Status: idle, running, failed")
    indexed_file_count: int = Field(default=0, nullable=False, description="Number of files indexed from this connector")


class Connector(ConnectorBase, table=True):  # type: ignore[call-arg]
    """Connector model for external data sources."""

    __tablename__ = "connectors"

    id: int = Field(default=None, primary_key=True)
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )


class ConnectorCreate(SQLModel):
    """Model for creating a connector."""

    space_id: int | None = None  # Optional, can use search_space_id instead
    search_space_id: int | None = None  # Alternative to space_id for frontend compatibility
    user_id: UUID | None = None  # Optional, will be set from current_user if not provided
    name: str
    connector_type: str
    is_enabled: bool = True
    config: dict | None = None

    # data-construction integration
    data_construction_folder_id: int | None = None

    # Periodic indexing fields
    periodic_indexing_enabled: bool | None = None
    indexing_frequency_minutes: int | None = None
    next_scheduled_at: datetime | None = None
    is_indexable: bool | None = None
    last_indexed_at: datetime | None = None

    # Indexing status
    indexing_status: str = "idle"
    indexed_file_count: int = 0

    def model_post_init(self, __context):
        """Normalize space_id from search_space_id if provided."""
        if self.search_space_id is not None and self.space_id is None:
            self.space_id = self.search_space_id
        elif self.space_id is None and self.search_space_id is None:
            raise ValueError("Either space_id or search_space_id must be provided")


class ConnectorUpdate(SQLModel):
    """Model for updating a connector."""

    name: str | None = None
    connector_type: str | None = None
    is_enabled: bool | None = None
    config: dict | None = None

    # data-construction integration
    data_construction_folder_id: int | None = None

    # Periodic indexing fields
    periodic_indexing_enabled: bool | None = None
    indexing_frequency_minutes: int | None = None
    next_scheduled_at: datetime | None = None
    is_indexable: bool | None = None
    last_indexed_at: datetime | None = None

    # Indexing status
    indexing_status: str | None = None
    indexed_file_count: int | None = None


class ConnectorRead(SQLModel):
    """Model for reading a connector."""

    id: int
    space_id: int
    user_id: UUID
    name: str
    connector_type: str
    is_enabled: bool
    config: dict
    created_at: datetime
    updated_at: datetime | None

    # data-construction integration
    data_construction_folder_id: int | None

    # Periodic indexing fields
    periodic_indexing_enabled: bool
    indexing_frequency_minutes: int | None
    next_scheduled_at: datetime | None
    is_indexable: bool
    last_indexed_at: datetime | None

    # Indexing status
    indexing_status: str
    indexed_file_count: int

    class Config:
        from_attributes = True
