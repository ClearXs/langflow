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
    GOOGLE_GMAIL_CONNECTOR = "GOOGLE_GMAIL_CONNECTOR"
    GOOGLE_CALENDAR_CONNECTOR = "GOOGLE_CALENDAR_CONNECTOR"


class ConnectorBase(SQLModel):
    """Base model for connector."""

    name: str = Field(max_length=255, nullable=False)
    connector_type: str = Field(max_length=50, nullable=False)
    is_enabled: bool = Field(default=True, nullable=False)
    config: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))


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

    space_id: int
    user_id: UUID
    name: str
    connector_type: str
    is_enabled: bool = True
    config: dict | None = None


class ConnectorUpdate(SQLModel):
    """Model for updating a connector."""

    name: str | None = None
    connector_type: str | None = None
    is_enabled: bool | None = None
    config: dict | None = None


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

    class Config:
        from_attributes = True
