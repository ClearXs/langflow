import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Column, DateTime, Field, SQLModel, Text, func

from langflow.schema.serialize import UUIDstr


def utc_now():
    return datetime.now(timezone.utc)


class DataSourceBase(SQLModel):
    """Base model for data source."""

    name: str = Field(index=True, nullable=False)
    type: str = Field(nullable=False)  # mysql, postgresql, hive, neo4j, kafka, flink, mongodb, clickhouse, doris
    host: str = Field(nullable=False)
    port: int = Field(nullable=False)
    database: str = Field(nullable=False)
    username: str | None = Field(default=None, nullable=True)  # Optional for Hive, Kafka, Flink
    password: str | None = Field(default=None, nullable=True)  # Optional for Hive, Kafka, Flink, store plain password (or you can encrypt it at application level)
    status: str | None = Field(default="inactive", nullable=True)  # active, inactive, error
    last_tested_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    advanced_config: str = Field(default="{}", sa_column=Column(Text, nullable=True, server_default="{}"))  # JSON string for advanced configuration


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
    username: str | None = None  # Optional for Hive, Kafka, Flink
    password: str | None = None  # Optional for Hive, Kafka, Flink
    advanced_config: dict | None = None  # Optional advanced configuration as dict


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
    advanced_config: dict | None = None  # Optional advanced configuration as dict


class DataSourceRead(SQLModel):
    """Model for reading a data source (without password)."""

    id: UUIDstr
    name: str
    type: str
    host: str
    port: int
    database: str
    username: str | None  # Optional for Hive, Kafka, Flink
    status: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    advanced_config: dict | None = None  # Advanced configuration as dict

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override model_validate to parse advanced_config JSON string to dict."""
        # If obj is a DataSource instance, parse advanced_config
        if hasattr(obj, "advanced_config"):
            # Create a dict from the ORM object
            data_dict = {
                "id": obj.id,
                "name": obj.name,
                "type": obj.type,
                "host": obj.host,
                "port": obj.port,
                "database": obj.database,
                "username": obj.username,
                "status": obj.status,
                "last_tested_at": obj.last_tested_at,
                "created_at": obj.created_at,
                "updated_at": obj.updated_at,
            }

            # Parse advanced_config from JSON string to dict
            if obj.advanced_config:
                try:
                    if isinstance(obj.advanced_config, str):
                        data_dict["advanced_config"] = json.loads(obj.advanced_config)
                    else:
                        data_dict["advanced_config"] = obj.advanced_config
                except (json.JSONDecodeError, TypeError):
                    data_dict["advanced_config"] = {}
            else:
                data_dict["advanced_config"] = {}

            # Call parent model_validate with the dict
            return super().model_validate(data_dict, **kwargs)

        # For dict input, use parent implementation
        return super().model_validate(obj, **kwargs)
