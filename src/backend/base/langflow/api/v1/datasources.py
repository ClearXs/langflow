"""Data source API routes."""

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
        # Create datasource with plain password
        db_datasource = DataSource(
            name=data.name,
            type=data.type,
            host=data.host,
            port=data.port,
            database=data.database,
            username=data.username,
            password=data.password,
            status="inactive",
        )

        session.add(db_datasource)
        await session.commit()
        await session.refresh(db_datasource)

        return DataSourceRead.model_validate(db_datasource)
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

        # Update fields
        if data.name is not None:
            datasource.name = data.name
        if data.type is not None:
            datasource.type = data.type
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

            # Use plain password from database
            connection_info = {
                "type": datasource.type,
                "host": datasource.host,
                "port": datasource.port,
                "database": datasource.database,
                "username": datasource.username,
                "password": datasource.password,
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
    try:
        datasource = await session.get(DataSource, datasource_id)
        if not datasource:
            raise HTTPException(status_code=404, detail="Data source not found")

        # Build connection info with password
        connection_info = {
            "type": datasource.type,
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": datasource.password,
        }

        # Use DataSourceManager to build connection string
        manager = DataSourceManager()
        connection_string = manager._build_connection_string(connection_info)

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

        # Build connection info with plain password
        connection_info = {
            "type": datasource.type,
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": datasource.password,
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

        # Build connection info with plain password
        connection_info = {
            "type": datasource.type,
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": datasource.password,
        }

        manager = DataSourceManager()
        columns = await manager.get_columns_from_connection(connection_info, table_name)
        return columns
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
