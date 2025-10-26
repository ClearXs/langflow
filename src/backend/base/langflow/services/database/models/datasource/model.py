from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Column, DateTime, Field, SQLModel, func

from langflow.schema.serialize import UUIDstr


def utc_now():
    return datetime.now(timezone.utc)


class DataSourceBase(SQLModel):
    """Base model for data source."""

    name: str = Field(index=True, nullable=False)
    type: str = Field(nullable=False)  # mysql, postgresql, oracle, mssql, mongodb, redis
    host: str = Field(nullable=False)
    port: int = Field(nullable=False)
    database: str = Field(nullable=False)
    username: str = Field(nullable=False)
    password: str = Field(nullable=False)  # Store plain password (or you can encrypt it at application level)
    status: str | None = Field(default="inactive", nullable=True)  # active, inactive, error
    last_tested_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

class DataSource(DataSourceBase, table=True):  # type: ignore[call-arg]
    """Data source model."""

    __tablename__ = "datasource"

    id: UUIDstr = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )


class DataSourceCreate(SQLModel):
    """Model for creating a data source."""

    name: str
    type: str
    host: str
    port: int
    database: str
    username: str
    password: str


class DataSourceUpdate(SQLModel):
    """Model for updating a data source."""

    name: str | None = None
    type: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    status: str | None = None
    last_tested_at: datetime | None = None


class DataSourceRead(SQLModel):
    """Model for reading a data source (without password)."""

    id: UUIDstr
    name: str
    type: str
    host: str
    port: int
    database: str
    username: str
    status: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
