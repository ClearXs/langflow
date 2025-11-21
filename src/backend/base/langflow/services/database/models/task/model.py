from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlmodel import JSON, Column, Field, SQLModel


class TaskBase(SQLModel):
    """Base model for flow execution task."""

    run_id: str = Field(index=True, unique=True, nullable=False)
    flow_id: UUID = Field(nullable=False, index=True)

    # Execution timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Task status: "running" | "success" | "error"
    # Logic: if any component has error status, task status is "error"
    status: str = Field(default="running", nullable=False, index=True)

    # Component statistics
    total_components: int = Field(default=0)
    success_components: int = Field(default=0)
    error_components: int = Field(default=0)

    # Data transfer statistics
    total_data_rows: int = Field(default=0)  # Sum of all component row_count
    total_data_size_mb: float = Field(default=0.0)  # Sum of all component data_size (MB)
    total_exchanges: int = Field(default=0)  # Total number of data exchanges

    # Performance statistics
    total_duration_ms: int | None = Field(default=None)  # Total execution time
    avg_memory_mb: float = Field(default=0.0)  # Average memory usage

    # User and trigger information
    user_id: UUID | None = Field(default=None)
    trigger_type: str = Field(default="manual")  # "manual" | "api" | "webhook"

    # Error information
    first_error_component_id: str | None = Field(default=None)
    first_error_message: str | None = Field(default=None)

    # Execution configuration
    execution_config: dict | None = Field(default=None, sa_column=Column(JSON))

    class Config:
        arbitrary_types_allowed = True

    @field_validator("flow_id", mode="before")
    @classmethod
    def validate_flow_id(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = UUID(value)
        return value

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = UUID(value)
        return value


class TaskTable(TaskBase, table=True):  # type: ignore[call-arg]
    """Database table for flow execution tasks."""

    __tablename__ = "flow_execution_task"
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)


class TaskReadResponse(TaskBase):
    """Response model for task read operations."""

    id: UUID = Field(alias="task_id")
    flow_id: UUID
