"""
Pydantic schemas for the chat feature with assistant-ui integration.

These schemas follow the assistant-ui ThreadHistoryAdapter pattern:
- ThreadRecord: id, title, archived, createdAt, updatedAt
- MessageRecord: id, threadId, role, content, createdAt
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from langflow.services.database.models.chat_message import ChatMessageRole

# =============================================================================
# Message Schemas
# =============================================================================


class ChatMessageBase(BaseModel):
    """Base schema for chat messages."""

    role: ChatMessageRole
    content: Any  # JSONB content - can be text, tool calls, etc.


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new message."""

    thread_id: int


class ChatMessageRead(ChatMessageBase):
    """Schema for reading a message."""

    id: int
    thread_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageAppend(BaseModel):
    """
    Schema for appending a message via the history adapter.
    This is the format assistant-ui sends when calling append().
    """

    role: str  # Accept string and validate in route handler
    content: Any


# =============================================================================
# Thread Schemas
# =============================================================================


class ChatThreadBase(BaseModel):
    """Base schema for chat threads."""

    title: str = Field(default="New Chat", max_length=500)
    archived: bool = False


class ChatThreadCreate(ChatThreadBase):
    """Schema for creating a new thread."""

    search_space_id: int


class ChatThreadUpdate(BaseModel):
    """Schema for updating a thread."""

    title: str | None = None
    archived: bool | None = None


class ChatThreadRead(ChatThreadBase):
    """
    Schema for reading a thread (matches assistant-ui ThreadRecord).
    """

    id: int
    search_space_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatThreadWithMessages(ChatThreadRead):
    """Schema for reading a thread with its messages."""

    messages: list[ChatMessageRead] = []


# =============================================================================
# History Adapter Response Schemas
# =============================================================================


class ThreadHistoryLoadResponse(BaseModel):
    """
    Response format for the ThreadHistoryAdapter.load() method.
    Returns messages array for the current thread.
    """

    messages: list[ChatMessageRead]


class ThreadListItem(BaseModel):
    """
    Thread list item for sidebar display.
    Matches assistant-ui ThreadListPrimitive expected format.
    """

    id: int
    title: str
    archived: bool
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ThreadListResponse(BaseModel):
    """Response containing list of threads for the sidebar."""

    threads: list[ThreadListItem]
    archived_threads: list[ThreadListItem]


# =============================================================================
# Chat Request Schemas (for deep agent)
# =============================================================================


class ChatMessage(BaseModel):
    """A single message in the chat history."""

    role: str  # "user" or "assistant"
    content: str


class ChatAttachment(BaseModel):
    """An attachment with its extracted content for chat context."""

    id: str  # Unique attachment ID
    name: str  # Original filename
    type: str  # Attachment type: document, image, audio
    content: str  # Extracted markdown content from the file


class ChatRequest(BaseModel):
    """Request schema for the deep agent chat endpoint."""

    chat_id: int
    user_query: str
    search_space_id: int
    messages: list[ChatMessage] | None = None  # Optional chat history from frontend
    attachments: list[ChatAttachment] | None = (
        None  # Optional attachments with extracted content
    )
    mentioned_document_ids: list[int] | None = (
        None  # Optional document IDs mentioned with @ in the chat
    )
