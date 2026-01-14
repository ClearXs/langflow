"""SpaceMembership model for Holo knowledge system."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func

if TYPE_CHECKING:
    from langflow.services.database.models.role import Role


def utc_now():
    return datetime.now(timezone.utc)


class SpaceMembershipBase(SQLModel):
    """Base model for space membership."""



class SpaceMembership(SpaceMembershipBase, table=True):  # type: ignore[call-arg]
    """SpaceMembership model for user-space-role mapping."""

    __tablename__ = "space_memberships"

    id: int = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    role_id: int = Field(foreign_key="roles.id", nullable=False, ondelete="CASCADE")
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    # Relationships
    role: "Role" = Relationship(back_populates="memberships")

    @property
    def is_owner(self) -> bool:
        """Check if this membership has the Owner role."""
        return self.role is not None and self.role.name == "Owner"


class SpaceMembershipCreate(SQLModel):
    """Model for creating a space membership."""

    user_id: UUID
    space_id: int
    role_id: int


class SpaceMembershipRead(SQLModel):
    """Model for reading a space membership."""

    id: int
    user_id: UUID
    space_id: int
    role_id: int
    created_at: datetime

    class Config:
        from_attributes = True
