"""Chat message model for Holo knowledge system."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column
from sqlmodel import JSON, DateTime, Field, SQLModel, func


def utc_now():
    return datetime.now(timezone.utc)


class ChatMessageRole(str, Enum):
    """Role enum for chat messages."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageBase(SQLModel):
    """Base model for chat message."""

    role: ChatMessageRole = Field(nullable=False)
    content: dict = Field(
        sa_column=Column(JSON, nullable=False), description="Message content stored as JSONB (text, tool calls, etc.)"
    )


class ChatMessage(ChatMessageBase, table=True):  # type: ignore[call-arg]
    """
    Message model for the new chat feature.
    Stores individual messages in assistant-ui format.
    """

    __tablename__ = "chat_messages"

    id: int = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="chat_threads.id", nullable=False, ondelete="CASCADE", index=True)
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class ChatMessageCreate(SQLModel):
    """Model for creating a chat message."""

    thread_id: int
    role: ChatMessageRole
    content: dict


class ChatMessageRead(SQLModel):
    """Model for reading a chat message."""

    id: int
    thread_id: int
    role: ChatMessageRole
    content: dict
    created_at: datetime

    class Config:
        from_attributes = True
