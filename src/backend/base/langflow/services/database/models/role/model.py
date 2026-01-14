"""Role model for Holo RBAC system."""

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Column
from sqlmodel import JSON, DateTime, Field, Relationship, SQLModel, func

if TYPE_CHECKING:
    from langflow.services.database.models.space_membership import SpaceMembership


def utc_now():
    return datetime.now(timezone.utc)


class Permission(str, Enum):
    """33 permission types for granular RBAC."""

    # Document permissions
    DOCUMENTS_CREATE = "documents:create"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_UPDATE = "documents:update"
    DOCUMENTS_DELETE = "documents:delete"
    # Chat permissions
    CHATS_CREATE = "chats:create"
    CHATS_READ = "chats:read"
    CHATS_UPDATE = "chats:update"
    CHATS_DELETE = "chats:delete"
    # LLM Config permissions
    LLM_CONFIGS_CREATE = "llm_configs:create"
    LLM_CONFIGS_READ = "llm_configs:read"
    LLM_CONFIGS_UPDATE = "llm_configs:update"
    LLM_CONFIGS_DELETE = "llm_configs:delete"
    # Connector permissions
    CONNECTORS_CREATE = "connectors:create"
    CONNECTORS_READ = "connectors:read"
    CONNECTORS_UPDATE = "connectors:update"
    CONNECTORS_DELETE = "connectors:delete"
    # Role permissions
    ROLES_CREATE = "roles:create"
    ROLES_READ = "roles:read"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"
    # Member permissions
    MEMBERS_CREATE = "members:create"
    MEMBERS_READ = "members:read"
    MEMBERS_UPDATE = "members:update"
    MEMBERS_DELETE = "members:delete"
    # Space permissions
    SPACES_UPDATE = "spaces:update"
    SPACES_DELETE = "spaces:delete"
    # Invite permissions
    INVITES_CREATE = "invites:create"
    INVITES_READ = "invites:read"
    INVITES_REVOKE = "invites:revoke"
    # Log permissions
    LOGS_READ = "logs:read"
    LOGS_DELETE = "logs:delete"
    # Podcast permissions
    PODCASTS_CREATE = "podcasts:create"
    PODCASTS_READ = "podcasts:read"
    # Full access
    FULL_ACCESS = "*"


DEFAULT_ROLE_PERMISSIONS = {
    "Owner": [Permission.FULL_ACCESS.value],
    "Admin": [
        Permission.DOCUMENTS_CREATE.value,
        Permission.DOCUMENTS_READ.value,
        Permission.DOCUMENTS_UPDATE.value,
        Permission.DOCUMENTS_DELETE.value,
        Permission.CHATS_CREATE.value,
        Permission.CHATS_READ.value,
        Permission.CHATS_UPDATE.value,
        Permission.CHATS_DELETE.value,
        Permission.LLM_CONFIGS_CREATE.value,
        Permission.LLM_CONFIGS_READ.value,
        Permission.LLM_CONFIGS_UPDATE.value,
        Permission.LLM_CONFIGS_DELETE.value,
        Permission.CONNECTORS_CREATE.value,
        Permission.CONNECTORS_READ.value,
        Permission.CONNECTORS_UPDATE.value,
        Permission.CONNECTORS_DELETE.value,
        Permission.ROLES_READ.value,
        Permission.MEMBERS_CREATE.value,
        Permission.MEMBERS_READ.value,
        Permission.MEMBERS_UPDATE.value,
        Permission.MEMBERS_DELETE.value,
        Permission.INVITES_CREATE.value,
        Permission.INVITES_READ.value,
        Permission.INVITES_REVOKE.value,
        Permission.LOGS_READ.value,
        Permission.PODCASTS_CREATE.value,
        Permission.PODCASTS_READ.value,
    ],
    "Editor": [
        Permission.DOCUMENTS_CREATE.value,
        Permission.DOCUMENTS_READ.value,
        Permission.DOCUMENTS_UPDATE.value,
        Permission.CHATS_CREATE.value,
        Permission.CHATS_READ.value,
        Permission.CHATS_UPDATE.value,
        Permission.LLM_CONFIGS_READ.value,
        Permission.CONNECTORS_READ.value,
        Permission.ROLES_READ.value,
        Permission.MEMBERS_READ.value,
        Permission.INVITES_READ.value,
        Permission.LOGS_READ.value,
        Permission.PODCASTS_CREATE.value,
        Permission.PODCASTS_READ.value,
    ],
    "Viewer": [
        Permission.DOCUMENTS_READ.value,
        Permission.CHATS_READ.value,
        Permission.LLM_CONFIGS_READ.value,
        Permission.CONNECTORS_READ.value,
        Permission.ROLES_READ.value,
        Permission.MEMBERS_READ.value,
        Permission.INVITES_READ.value,
        Permission.LOGS_READ.value,
        Permission.PODCASTS_READ.value,
    ],
}


class RoleBase(SQLModel):
    """Base model for role."""

    name: str = Field(max_length=100, nullable=False)
    description: str | None = Field(default=None, max_length=500, nullable=True)
    is_custom: bool = Field(default=True, nullable=False)
    is_default: bool = Field(default=False, nullable=False)
    is_system_role: bool = Field(default=False, nullable=False)


class Role(RoleBase, table=True):  # type: ignore[call-arg]
    """Role model for RBAC."""

    __tablename__ = "roles"

    id: int = Field(default=None, primary_key=True)
    search_space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    permissions: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]"))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )

    # Relationships
    memberships: list["SpaceMembership"] = Relationship(back_populates="role")


class RoleCreate(SQLModel):
    """Model for creating a role."""

    search_space_id: int
    name: str
    description: str | None = None
    permissions: list[str]
    is_custom: bool = True


class RoleUpdate(SQLModel):
    """Model for updating a role."""

    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class RoleRead(SQLModel):
    """Model for reading a role."""

    id: int
    search_space_id: int
    name: str
    description: str | None
    permissions: list[str]
    is_custom: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


def has_permission(user_permissions: list[str], required_permission: str) -> bool:
    """Check if the user has the required permission.
    Supports wildcard (*) for full access.

    Args:
        user_permissions: List of permission strings the user has
        required_permission: The permission string to check for

    Returns:
        True if user has the permission, False otherwise
    """
    if not user_permissions:
        return False

    # Full access wildcard grants all permissions
    if Permission.FULL_ACCESS.value in user_permissions:
        return True

    return required_permission in user_permissions
