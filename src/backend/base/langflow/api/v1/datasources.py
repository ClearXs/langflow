"""Data source API routes."""

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from lfx.base.datasource.manager import DataSourceManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from langflow.services.database.models.datasource import (
    DataSource,
    DataSourceCreate,
    DataSourceRead,
    DataSourceUpdate,
)
from langflow.services.database.models.datasource.schemas import validate_advanced_config
from langflow.services.deps import get_session

router = APIRouter(prefix="/api/v1/datasources", tags=["datasources"])


@router.get("", response_model=list[DataSourceRead])
async def get_datasources(session: AsyncSession = Depends(get_session)) -> list[DataSourceRead]:
    """Get all data sources.

    Returns:
        List of all data sources (without passwords)
    """
    try:
        statement = select(DataSource)
        result = await session.exec(statement)
        datasources = result.all()
        return [DataSourceRead.model_validate(ds) for ds in datasources]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{datasource_id}", response_model=DataSourceRead)
async def get_datasource(datasource_id: UUID, session: AsyncSession = Depends(get_session)) -> DataSourceRead:
    """Get a specific data source by ID.

    Args:
        datasource_id: Data source ID

    Returns:
        Data source details (without password)
    """
    try:
        datasource = await session.get(DataSource, datasource_id)
        if not datasource:
            raise HTTPException(status_code=404, detail="Data source not found")
        return DataSourceRead.model_validate(datasource)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=DataSourceRead)
async def create_datasource(data: DataSourceCreate, session: AsyncSession = Depends(get_session)) -> DataSourceRead:
    """Create a new data source.

    Args:
        data: Data source configuration

    Returns:
        Created data source (without password)
    """
    try:
        # Validate database type - support MySQL, PostgreSQL, Hive, Neo4j, Kafka, Flink, MongoDB, ClickHouse, Doris
        allowed_types = ["mysql", "postgresql", "hive", "neo4j", "kafka", "flink", "mongodb", "clickhouse", "doris"]
        db_type_lower = data.type.lower()
        if db_type_lower not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported database type: {data.type}. Supported types: {', '.join(allowed_types)}",
            )

        # Validate username and password requirements
        # For Hive, Kafka, and Flink, username and password are optional
        # For other types (MySQL, PostgreSQL, Neo4j, MongoDB, ClickHouse, Doris), they are required
        if db_type_lower not in ["hive", "kafka", "flink"]:
            if not data.username or not data.password:
                raise HTTPException(
                    status_code=400, detail=f"Username and password are required for {data.type} database type"
                )

        # Validate advanced_config if provided
        if data.advanced_config:
            is_valid, errors = validate_advanced_config(db_type_lower, data.advanced_config)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid advanced configuration: {'; '.join(errors)}")

        # Convert advanced_config dict to JSON string for storage
        advanced_config_str = json.dumps(data.advanced_config) if data.advanced_config else "{}"

        # Create datasource with plain password
        db_datasource = DataSource(
            name=data.name,
            type=db_type_lower,  # Normalize to lowercase
            host=data.host,
            port=data.port,
            database=data.database,
            username=data.username,
            password=data.password,
            status="inactive",
            advanced_config=advanced_config_str,
        )

        session.add(db_datasource)
        await session.commit()
        await session.refresh(db_datasource)

        return DataSourceRead.model_validate(db_datasource)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{datasource_id}", response_model=DataSourceRead)
async def update_datasource(
    datasource_id: UUID, data: DataSourceUpdate, session: AsyncSession = Depends(get_session)
) -> DataSourceRead:
    """Update an existing data source.

    Args:
        datasource_id: Data source ID
        data: Updated configuration

    Returns:
        Updated data source (without password)
    """
    try:
        # Get existing datasource
        datasource = await session.get(DataSource, datasource_id)
        if not datasource:
            raise HTTPException(status_code=404, detail="Data source not found")

        # Validate database type if being updated
        if data.type is not None:
            allowed_types = ["mysql", "postgresql", "hive", "neo4j", "kafka", "flink", "mongodb", "clickhouse", "doris"]
            db_type_lower = data.type.lower()
            if db_type_lower not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported database type: {data.type}. Supported types: {', '.join(allowed_types)}",
                )
            datasource.type = db_type_lower

        # Validate advanced_config if being updated
        if data.advanced_config is not None:
            # Use current type or updated type for validation
            validate_type = data.type.lower() if data.type else datasource.type
            is_valid, errors = validate_advanced_config(validate_type, data.advanced_config)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid advanced configuration: {'; '.join(errors)}")

        # Update fields
        if data.name is not None:
            datasource.name = data.name
        if data.host is not None:
            datasource.host = data.host
        if data.port is not None:
            datasource.port = data.port
        if data.database is not None:
            datasource.database = data.database
        if data.username is not None:
            datasource.username = data.username
        if data.password is not None:
            datasource.password = data.password
        if data.status is not None:
            datasource.status = data.status
        if data.last_tested_at is not None:
            datasource.last_tested_at = data.last_tested_at
        if data.advanced_config is not None:
            datasource.advanced_config = json.dumps(data.advanced_config)

        session.add(datasource)
        await session.commit()
        await session.refresh(datasource)

        return DataSourceRead.model_validate(datasource)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{datasource_id}")
async def delete_datasource(datasource_id: UUID, session: AsyncSession = Depends(get_session)):
    """Delete a data source.

    Args:
        datasource_id: Data source ID
    """
    try:
        datasource = await session.get(DataSource, datasource_id)
        if not datasource:
            raise HTTPException(status_code=404, detail="Data source not found")

        await session.delete(datasource)
        await session.commit()

        return {"message": "Data source deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test")
async def test_connection(data: dict, session: AsyncSession = Depends(get_session)):
    """Test a data source connection.

    Args:
        data: Connection parameters (can include datasource_id or direct connection info)

    Returns:
        Test result
    """
    try:
        connection_info = {}

        # If datasource_id is provided, load from database
        if data.get("datasource_id"):
            datasource_id = UUID(data["datasource_id"])
            datasource = await session.get(DataSource, datasource_id)
            if not datasource:
                raise HTTPException(status_code=404, detail="Data source not found")

            # Parse advanced_config from JSON string
            advanced_config = {}
            if datasource.advanced_config:
                try:
                    advanced_config = json.loads(datasource.advanced_config)
                except (json.JSONDecodeError, TypeError):
                    advanced_config = {}

            # Use plain password from database
            connection_info = {
                "type": datasource.type,
                "host": datasource.host,
                "port": datasource.port,
                "database": datasource.database,
                "username": datasource.username,
                "password": datasource.password,
                "advanced_config": advanced_config,
            }
        else:
            # Use provided connection parameters
            connection_info = {
                "type": data.get("type"),
                "host": data.get("host"),
                "port": data.get("port"),
                "database": data.get("database"),
                "username": data.get("username"),
                # Password must be provided for test
                "password": data.get("password"),
                "advanced_config": data.get("advanced_config", {}),
            }

        # Test connection using DataSourceManager
        manager = DataSourceManager()
        result = await manager.test_connection(connection_info)

        # If testing an existing datasource, update its status
        if data.get("datasource_id"):
            datasource.status = "active" if result["status"] == "success" else "error"
            datasource.last_tested_at = datetime.now(timezone.utc)
            session.add(datasource)
            await session.commit()

        return result
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "failed", "message": str(e)}


@router.get("/{datasource_id}/connection-string")
async def get_connection_string(datasource_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    """Get connection string for a datasource (for internal use).

    Args:
        datasource_id: Data source ID

    Returns:
        Dict with connection_string
    """
    import structlog

    logger = structlog.get_logger(__name__)

    try:
        datasource = await session.get(DataSource, datasource_id)
        if not datasource:
            raise HTTPException(status_code=404, detail="Data source not found")

        # 🔍 调试日志：检查从数据库读取的密码
        logger.info(
            f"[API] Datasource {datasource.name} (type={datasource.type}): "
            f"username={datasource.username}, "
            f"password_length={len(datasource.password) if datasource.password else 0}, "
            f"password_is_none={datasource.password is None}"
        )

        # Parse advanced_config from JSON string
        advanced_config = {}
        if datasource.advanced_config:
            try:
                advanced_config = json.loads(datasource.advanced_config)
            except (json.JSONDecodeError, TypeError):
                advanced_config = {}

        # Build connection info with password and advanced_config
        connection_info = {
            "type": datasource.type,
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": datasource.password,
            "advanced_config": advanced_config,
        }

        # Use DataSourceManager to build connection string
        manager = DataSourceManager()
        connection_string = manager._build_connection_string(connection_info)

        # 🔍 调试日志：检查生成的连接字符串
        # 隐藏密码部分用于安全日志
        import re

        safe_conn_str = re.sub(r"://([^:]+):([^@]*)@", r"://\1:***@", connection_string)
        logger.info(f"[API] Built connection string: {safe_conn_str}")

        return {"connection_string": connection_string}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{datasource_id}/tables")
async def get_tables(datasource_id: UUID, session: AsyncSession = Depends(get_session)) -> list[str]:
    """Get list of tables for a data source.

    Args:
        datasource_id: Data source ID

    Returns:
        List of table names
    """
    try:
        datasource = await session.get(DataSource, datasource_id)
        if not datasource:
            raise HTTPException(status_code=404, detail="Data source not found")

        # Parse advanced_config from JSON string
        advanced_config = {}
        if datasource.advanced_config:
            try:
                advanced_config = json.loads(datasource.advanced_config)
            except (json.JSONDecodeError, TypeError):
                advanced_config = {}

        # Build connection info with plain password and advanced_config
        connection_info = {
            "type": datasource.type,
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": datasource.password,
            "advanced_config": advanced_config,
        }

        manager = DataSourceManager()
        tables = await manager.get_tables_from_connection(connection_info)
        return tables
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{datasource_id}/tables/{table_name}/columns")
async def get_columns(datasource_id: UUID, table_name: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    """Get list of columns for a table.

    Args:
        datasource_id: Data source ID
        table_name: Table name

    Returns:
        List of column information
    """
    try:
        datasource = await session.get(DataSource, datasource_id)
        if not datasource:
            raise HTTPException(status_code=404, detail="Data source not found")

        # Parse advanced_config from JSON string
        advanced_config = {}
        if datasource.advanced_config:
            try:
                advanced_config = json.loads(datasource.advanced_config)
            except (json.JSONDecodeError, TypeError):
                advanced_config = {}

        # Build connection info with plain password and advanced_config
        connection_info = {
            "type": datasource.type,
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": datasource.password,
            "advanced_config": advanced_config,
        }

        manager = DataSourceManager()
        columns = await manager.get_columns_from_connection(connection_info, table_name)
        return columns
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
