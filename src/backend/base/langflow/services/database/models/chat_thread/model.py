"""Chat thread model for Holo knowledge system."""

from datetime import datetime, timezone

from sqlalchemy import Column
from sqlmodel import DateTime, Field, SQLModel, String, func


def utc_now():
    return datetime.now(timezone.utc)


class ChatThreadBase(SQLModel):
    """Base model for chat thread."""

    title: str = Field(max_length=500, nullable=False, index=True, default="New Chat")
    archived: bool = Field(default=False, nullable=False)


class ChatThread(ChatThreadBase, table=True):  # type: ignore[call-arg]
    """
    Thread model for the new chat feature using assistant-ui.
    Each thread represents a conversation with message history.
    LangGraph checkpointer uses thread_id for state persistence.
    """

    __tablename__ = "chat_threads"

    id: int = Field(default=None, primary_key=True)
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE", description="Foreign key to spaces")
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True
        ),
    )


class ChatThreadCreate(SQLModel):
    """Model for creating a chat thread."""

    space_id: int
    title: str = "New Chat"
    archived: bool = False


class ChatThreadUpdate(SQLModel):
    """Model for updating a chat thread."""

    title: str | None = None
    archived: bool | None = None


class ChatThreadRead(SQLModel):
    """Model for reading a chat thread."""

    id: int
    space_id: int
    title: str
    archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
