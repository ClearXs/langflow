import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.connector import Connector, ConnectorType

logger = logging.getLogger(__name__)

router = APIRouter()


class AddLumaConnectorRequest(BaseModel):
    """Request model for adding a Luma connector."""

    api_key: str = Field(..., description="Luma API key")
    space_id: int = Field(..., description="Search space ID")


@router.post("/connectors/luma/add")
async def add_luma_connector(
    request: AddLumaConnectorRequest,
    current_user: CurrentActiveUser = None,
    db: DbSession = None,
):
    """Add a new Luma connector for the authenticated user.

    Args:
        request: The request containing Luma API key and space_id
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message and connector details

    Raises:
        HTTPException: If connector already exists or validation fails
    """
    try:
        # Check if a Luma connector already exists for this search space and user
        result = await db.execute(
            select(Connector).filter(
                Connector.search_space_id == request.space_id,
                Connector.user_id == current_user.id,
                Connector.connector_type
                == ConnectorType.LUMA_CONNECTOR,
            )
        )
        existing_connector = result.scalars().first()

        if existing_connector:
            # Update existing connector with new API key
            existing_connector.config = {"api_key": request.api_key}
            existing_connector.is_indexable = True
            await db.commit()
            await db.refresh(existing_connector)

            logger.info(
                f"Updated existing Luma connector for user {current_user.id} in space {request.space_id}"
            )

            return {
                "message": "Luma connector updated successfully",
                "connector_id": existing_connector.id,
                "connector_type": "LUMA_CONNECTOR",
            }

        # Create new Luma connector
        db_connector = Connector(
            name="Luma Event Connector",
            connector_type=ConnectorType.LUMA_CONNECTOR,
            config={"api_key": request.api_key},
            search_space_id=request.space_id,
            user_id=current_user.id,
            is_indexable=True,
        )

        db.add(db_connector)
        await db.commit()
        await db.refresh(db_connector)

        logger.info(
            f"Successfully created Luma connector for user {current_user.id} with ID {db_connector.id}"
        )

        return {
            "message": "Luma connector added successfully",
            "connector_id": db_connector.id,
            "connector_type": "LUMA_CONNECTOR",
        }

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Database integrity error: {e!s}")
        raise HTTPException(
            status_code=409,
            detail="A Luma connector already exists for this user.",
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error adding Luma connector: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add Luma connector: {e!s}",
        ) from e


@router.delete("/connectors/luma")
async def delete_luma_connector(
    space_id: int,
    current_user: CurrentActiveUser = None,
    db: DbSession = None,
):
    """Delete the Luma connector for the authenticated user in a specific search space.

    Args:
        space_id: Search space ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If connector doesn't exist
    """
    try:
        result = await db.execute(
            select(Connector).filter(
                Connector.search_space_id == space_id,
                Connector.user_id == current_user.id,
                Connector.connector_type
                == ConnectorType.LUMA_CONNECTOR,
            )
        )
        connector = result.scalars().first()

        if not connector:
            raise HTTPException(
                status_code=404,
                detail="Luma connector not found for this user.",
            )

        await db.delete(connector)
        await db.commit()

        logger.info(f"Successfully deleted Luma connector for user {current_user.id}")

        return {"message": "Luma connector deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error deleting Luma connector: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Luma connector: {e!s}",
        ) from e


@router.get("/connectors/luma/test")
async def test_luma_connector(
    space_id: int,
    current_user: CurrentActiveUser = None,
    db: DbSession = None,
):
    """Test the Luma connector for the authenticated user in a specific search space.

    Args:
        space_id: Search space ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Test results including user info and event count

    Raises:
        HTTPException: If connector doesn't exist or test fails
    """
    try:
        # Get the Luma connector for this search space and user
        result = await db.execute(
            select(Connector).filter(
                Connector.search_space_id == space_id,
                Connector.user_id == current_user.id,
                Connector.connector_type
                == ConnectorType.LUMA_CONNECTOR,
            )
        )
        connector = result.scalars().first()

        if not connector:
            raise HTTPException(
                status_code=404,
                detail="Luma connector not found. Please add a connector first.",
            )

        # Import LumaConnector
        from langflow.connectors.luma_connector import LumaConnector

        # Initialize the connector
        api_key = connector.config.get("api_key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="Invalid connector configuration: API key missing.",
            )

        luma = LumaConnector(api_key=api_key)

        # Test the connection by fetching user info
        user_info, error = luma.get_user_info()
        if error:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to Luma: {error}",
            )

        # Try to fetch events
        events, events_error = luma.get_all_events(limit=10)

        return {
            "message": "Luma connector is working correctly",
            "user_info": {
                "name": user_info.get("name", "Unknown"),
                "email": user_info.get("email", "Unknown"),
            },
            "event_count": len(events) if not events_error else 0,
            "events_error": events_error,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error testing Luma connector: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test Luma connector: {e!s}",
        ) from e
