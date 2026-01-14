"""SpaceInvite model for Holo knowledge system."""

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Column, DateTime, Field, SQLModel, func


def utc_now():
    return datetime.now(timezone.utc)


class SpaceInviteBase(SQLModel):
    """Base model for space invite."""

    email: str = Field(max_length=255, nullable=False)
    token: str = Field(max_length=255, nullable=False, unique=True, index=True)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    is_used: bool = Field(default=False, nullable=False)


class SpaceInvite(SpaceInviteBase, table=True):  # type: ignore[call-arg]
    """SpaceInvite model for inviting users to spaces."""

    __tablename__ = "space_invites"

    id: int = Field(default=None, primary_key=True)
    space_id: int = Field(foreign_key="spaces.id", nullable=False, ondelete="CASCADE")
    role_id: int = Field(foreign_key="roles.id", nullable=False, ondelete="CASCADE")
    inviter_id: UUID = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )


class SpaceInviteCreate(SQLModel):
    """Model for creating a space invite."""

    space_id: int
    role_id: int
    inviter_id: UUID
    email: str
    token: str
    expires_at: datetime


class SpaceInviteRead(SQLModel):
    """Model for reading a space invite."""

    id: int
    space_id: int
    role_id: int
    inviter_id: UUID
    email: str
    token: str
    expires_at: datetime
    is_used: bool
    created_at: datetime

    class Config:
        from_attributes = True
