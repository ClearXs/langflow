"""Response schemas for API endpoints."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Import schemas from database models for type hints
from langflow.services.database.models import ChunkRead, SpaceRead


# RBAC-related request/response schemas
class LLMPreferencesRead(BaseModel):
    """LLM preferences for a space."""

    document_summary_llm_id: int | None
    chatbot_default_llm_id: int | None


class LLMPreferencesUpdate(BaseModel):
    """Update LLM preferences."""

    document_summary_llm_id: int | None = None
    chatbot_default_llm_id: int | None = None


class InviteAcceptRequest(BaseModel):
    """Request to accept an invite."""

    invite_code: str


class InviteInfoResponse(BaseModel):
    """Response with invite information."""

    invite_code: str
    space_id: int
    space_name: str
    inviter_name: str | None
    role_name: str
    created_at: datetime
    expires_at: datetime | None
    is_expired: bool


class InviteAcceptResponse(BaseModel):
    """Response after accepting an invite."""

    message: str
    space_id: int
    role_name: str


class InviteUpdate(BaseModel):
    """Update model for invites."""

    role_id: int | None = None
    expires_at: datetime | None = None


class MembershipUpdate(BaseModel):
    """Update model for memberships."""

    role_id: int | None = None


class DefaultSystemInstructionsResponse(BaseModel):
    """Response for default system instructions."""

    default_system_instructions: str


class GlobalLLMConfigRead(BaseModel):
    """Read model for global LLM configurations (API keys hidden)."""

    id: int
    name: str
    provider: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int | None = None
    system_instructions: str | None = None
    enable_citation: bool = True
    is_global: bool = True

    class Config:
        from_attributes = True

# Type variable for generic pagination
T = TypeVar("T")


class ExtensionDocumentMetadata(BaseModel):
    """Metadata for extension documents."""

    VisitedWebPageTitle: str
    VisitedWebPageURL: str
    BrowsingSessionId: str
    VisitedWebPageDateWithTimeInISOString: str
    VisitedWebPageVisitDurationInMilliseconds: int
    VisitedWebPageReffererURL: str | None = None


class ExtensionDocument(BaseModel):
    """Extension document with metadata."""

    metadata: ExtensionDocumentMetadata
    pageContent: str


class DocumentsCreate(BaseModel):
    """Schema for bulk document creation."""

    search_space_id: int
    document_type: str
    content: list[ExtensionDocument] | list[str]  # List of ExtensionDocument or list of URLs


class DocumentWithChunksRead(BaseModel):
    """Document with its chunks."""

    id: int
    title: str
    document_type: str
    document_metadata: dict
    content: str
    content_hash: str | None
    unique_identifier_hash: str
    created_at: datetime
    updated_at: datetime | None
    search_space_id: int
    chunks: list[ChunkRead]

    class Config:
        from_attributes = True


class SpaceWithStats(BaseModel):
    """Space with statistics."""

    space: SpaceRead
    document_count: int = 0
    connector_count: int = 0
    member_count: int = 0

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = Field(default=0)

    def __init__(self, **data):
        super().__init__(**data)
        if self.page_size > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size

    class Config:
        from_attributes = True


class PermissionInfo(BaseModel):
    """Permission information."""

    name: str
    description: str
    category: str

    class Config:
        from_attributes = True


class PermissionsListResponse(BaseModel):
    """List of all available permissions."""

    permissions: list[PermissionInfo]

    class Config:
        from_attributes = True


class UserSpaceAccess(BaseModel):
    """User's access to a space."""

    space_id: int
    space_name: str
    role_name: str
    permissions: list[str]

    class Config:
        from_attributes = True


__all__ = [
    "DefaultSystemInstructionsResponse",
    "DocumentsCreate",
    "DocumentWithChunksRead",
    "ExtensionDocument",
    "ExtensionDocumentMetadata",
    "GlobalLLMConfigRead",
    "InviteAcceptRequest",
    "InviteAcceptResponse",
    "InviteInfoResponse",
    "InviteUpdate",
    "LLMPreferencesRead",
    "LLMPreferencesUpdate",
    "MembershipUpdate",
    "PaginatedResponse",
    "PermissionInfo",
    "PermissionsListResponse",
    "SpaceWithStats",
    "UserSpaceAccess",
]
