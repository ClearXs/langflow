from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import field_serializer
from sqlmodel import JSON, Column, Field, SQLModel

from langflow.serialization.serialization import get_max_items_length, get_max_text_length, serialize


class DataExchangeBase(SQLModel):
    """Base model for data exchange between components."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    transaction_id: UUID = Field(nullable=False, index=True)
    source_vertex_id: str = Field(nullable=False, index=True)
    target_vertex_id: str = Field(nullable=False, index=True)
    exchange_type: str = Field(default="direct")  # direct, broadcast, conditional, aggregated
    data_type: str = Field(nullable=False)  # e.g., "Message", "Data", "str", "list"
    data_size: int = Field(default=0)  # Size in bytes
    data_sample: dict | None = Field(default=None, sa_column=Column(JSON))  # Sampled data content
    exchange_metadata: dict | None = Field(
        default=None, sa_column=Column(JSON)
    )  # Additional metadata (renamed to avoid SQLModel conflict)

    # Needed for Column(JSON)
    class Config:
        arbitrary_types_allowed = True

    @field_serializer("data_sample")
    def serialize_data_sample(self, data) -> dict | None:
        """Serialize the data sample with enforced limits on text length and item count.

        Parameters:
            data (dict): The data sample to be serialized.

        Returns:
            dict | None: The serialized data sample with applied constraints.
        """
        if data is None:
            return None
        return serialize(data, max_length=get_max_text_length(), max_items=get_max_items_length())


class DataExchangeTable(DataExchangeBase, table=True):  # type: ignore[call-arg]
    """Database table for storing data exchange records between components."""

    __tablename__ = "data_exchange"
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)


class DataExchangeReadResponse(DataExchangeBase):
    """Response model for data exchange records."""

    id: UUID
    transaction_id: UUID


class DataExchangeStatsResponse(SQLModel):
    """Response model for aggregated data exchange statistics."""

    total_exchanges: int = Field(default=0)
    total_data_size: int = Field(default=0)  # Total size in bytes
    unique_source_vertices: int = Field(default=0)
    unique_target_vertices: int = Field(default=0)
    exchange_by_type: dict[str, int] = Field(default_factory=dict)  # {"direct": 100, "broadcast": 20}
    avg_data_size: float = Field(default=0.0)


class VertexExchangeResponse(SQLModel):
    """Response model for a vertex's data exchange summary."""

    vertex_id: str
    input_exchanges: list[DataExchangeReadResponse] = Field(default_factory=list)
    output_exchanges: list[DataExchangeReadResponse] = Field(default_factory=list)
    total_input_count: int = Field(default=0)
    total_output_count: int = Field(default=0)
    total_input_size: int = Field(default=0)
    total_output_size: int = Field(default=0)
