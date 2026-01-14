"""Podcast model for Holo knowledge system."""

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import JSON, Column, DateTime, Field, SQLModel, Text, func


def utc_now():
    return datetime.now(timezone.utc)


class PodcastBase(SQLModel):
    """Base model for podcast."""

    title: str = Field(max_length=500, nullable=False)
    podcast_transcript: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    file_location: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    duration_seconds: int | None = Field(default=None, nullable=True)


class Podcast(PodcastBase, table=True):  # type: ignore[call-arg]
    """Podcast model."""

    __tablename__ = "podcasts"

    id: int = Field(default=None, primary_key=True)
    search_space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class PodcastCreate(SQLModel):
    """Model for creating a podcast."""

    search_space_id: int
    user_id: UUID
    title: str
    podcast_transcript: dict | None = None
    file_location: str | None = None
    duration_seconds: int | None = None


class PodcastUpdate(SQLModel):
    """Model for updating a podcast."""

    title: str | None = None
    podcast_transcript: dict | None = None
    file_location: str | None = None
    duration_seconds: int | None = None


class PodcastRead(SQLModel):
    """Model for reading a podcast."""

    id: int
    search_space_id: int
    user_id: UUID
    title: str
    podcast_transcript: dict | None
    file_location: str | None
    duration_seconds: int | None
    created_at: datetime

    class Config:
        from_attributes = True
