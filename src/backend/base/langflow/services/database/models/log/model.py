"""Log model for Holo knowledge system."""

from datetime import datetime, timezone
from enum import Enum

from sqlmodel import JSON, Column, DateTime, Field, SQLModel, Text, func


def utc_now():
    return datetime.now(timezone.utc)


class LogLevel(str, Enum):
    """Log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogStatus(str, Enum):
    """Log operation status."""

    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class LogBase(SQLModel):
    """Base model for log."""

    level: str = Field(max_length=20, nullable=False)
    status: str = Field(max_length=20, nullable=False)
    message: str = Field(sa_column=Column(Text, nullable=False))
    source: str | None = Field(default=None, max_length=100, nullable=True)
    log_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))


class Log(LogBase, table=True):  # type: ignore[call-arg]
    """Log model for system operations."""

    __tablename__ = "logs"

    id: int = Field(default=None, primary_key=True)
    search_space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class LogCreate(SQLModel):
    """Model for creating a log."""

    search_space_id: int
    level: str
    status: str
    message: str
    source: str | None = None
    log_metadata: dict | None = None


class LogRead(SQLModel):
    """Model for reading a log."""

    id: int
    search_space_id: int
    level: str
    status: str
    message: str
    source: str | None
    log_metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True


class LogUpdate(SQLModel):
    """Model for updating a log."""

    level: str | None = None
    status: str | None = None
    message: str | None = None
    source: str | None = None
    log_metadata: dict | None = None
