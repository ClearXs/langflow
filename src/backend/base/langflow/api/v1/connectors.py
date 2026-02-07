"""Connector routes for CRUD operations:
POST /connectors/ - Create a new connector
GET /connectors/ - List all connectors for the current user (optionally filtered by search space)
GET /connectors/{connector_id} - Get a specific connector
PUT /connectors/{connector_id} - Update a specific connector
DELETE /connectors/{connector_id} - Delete a specific connector
POST /connectors/{connector_id}/index - Index content from a connector to a search space

Note: Each search space can have only one connector of each type per user (based on search_space_id, user_id, and connector_type).
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.connectors.github_connector import GitHubConnector
from langflow.services.database.models.connector import (
    Connector,
    ConnectorBase,
    ConnectorCreate,
    ConnectorRead,
    ConnectorType,
    ConnectorUpdate,
)
from langflow.utils.periodic_scheduler import (
    create_periodic_schedule,
    delete_periodic_schedule,
    update_periodic_schedule,
)
from langflow.utils.rbac import check_permission
from langflow.workers.connector_tasks import (
    index_airtable_records_task,
    index_bookstack_pages_task,
    index_clickup_tasks_task,
    index_confluence_pages_task,
    index_crawled_urls_task,
    index_discord_messages_task,
    index_elasticsearch_documents_task,
    index_github_repos_task,
    index_google_calendar_events_task,
    index_google_gmail_messages_task,
    index_jira_issues_task,
    index_linear_issues_task,
    index_luma_events_task,
    index_notion_pages_task,
    index_slack_messages_task,
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


# Use Pydantic's BaseModel here
class GitHubPATRequest(BaseModel):
    github_pat: str = Field(..., description="GitHub Personal Access Token")


# --- New Endpoint to list GitHub Repositories ---
@router.post("/github/repositories", response_model=list[dict[str, Any]])
async def list_github_repositories(
    pat_request: GitHubPATRequest,
    current_user: CurrentActiveUser = None,  # Ensure the user is logged in
):
    """Fetches a list of repositories accessible by the provided GitHub PAT.
    The PAT is used for this request only and is not stored.
    """
    try:
        # Initialize GitHubConnector with the provided PAT
        github_client = GitHubConnector(token=pat_request.github_pat)
        # Fetch repositories
        repositories = github_client.get_user_repositories()
        return repositories
    except ValueError as e:
        # Handle invalid token error specifically
        logger.error(f"GitHub PAT validation failed for user {current_user.id}: {e!s}")
        raise HTTPException(status_code=400, detail=f"Invalid GitHub PAT: {e!s}") from e
    except Exception as e:
        logger.error(f"Failed to fetch GitHub repositories for user {current_user.id}: {e!s}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch GitHub repositories."
        ) from e


@router.post("/", response_model=ConnectorRead)
async def create_connector(
    connector: ConnectorCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Create a new connector.
    Requires CONNECTORS_CREATE permission.

    Each search space can have only one connector of each type (based on space_id and connector_type).
    The config must contain the appropriate keys for the connector type.
    """
    try:
        # Normalize space_id from search_space_id if needed
        if connector.search_space_id is not None and connector.space_id is None:
            connector.space_id = connector.search_space_id

        # Validate that space_id is provided
        if connector.space_id is None:
            raise HTTPException(
                status_code=422,
                detail="Either space_id or search_space_id must be provided",
            )

        # Automatically set user_id from current_user if not provided
        if connector.user_id is None:
            connector.user_id = current_user.id

        # Check if user has permission to create connectors
        await check_permission(
            db,
            current_user,
            connector.space_id,
            "CONNECTORS_CREATE",
            "You don't have permission to create connectors in this search space",
        )

        # Check if a connector with the same type already exists for this search space
        result = await db.execute(
            select(Connector).filter(
                Connector.space_id == connector.space_id,
                Connector.connector_type == connector.connector_type,
            )
        )
        existing_connector = result.scalars().first()
        if existing_connector:
            raise HTTPException(
                status_code=409,
                detail=f"A connector with type {connector.connector_type} already exists in this search space.",
            )

        # Prepare connector data
        connector_data = connector.model_dump()

        # Automatically set next_scheduled_at if periodic indexing is enabled
        if (
            connector.periodic_indexing_enabled
            and connector.indexing_frequency_minutes
            and connector.next_scheduled_at is None
        ):
            connector_data["next_scheduled_at"] = datetime.now(UTC) + timedelta(
                minutes=connector.indexing_frequency_minutes
            )

        db_connector = Connector(**connector_data)
        db.add(db_connector)
        await db.commit()
        await db.refresh(db_connector)

        # Create periodic schedule if periodic indexing is enabled
        if (
            db_connector.periodic_indexing_enabled
            and db_connector.indexing_frequency_minutes
        ):
            success = create_periodic_schedule(
                connector_id=db_connector.id,
                search_space_id=db_connector.space_id,
                user_id=str(current_user.id),
                connector_type=db_connector.connector_type,
                frequency_minutes=db_connector.indexing_frequency_minutes,
            )
            if not success:
                logger.warning(
                    f"Failed to create periodic schedule for connector {db_connector.id}"
                )

        return db_connector
    except ValidationError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation error: {e!s}") from e
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Integrity error: A connector with this type already exists in this search space. {e!s}",
        ) from e
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Failed to create connector: {e!s}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create connector: {e!s}",
        ) from e


@router.get("/", response_model=list[ConnectorRead])
async def read_connectors(
    skip: int = 0,
    limit: int = 100,
    search_space_id: int = Query(..., description="ID of the search space to filter connectors"),
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """List all connectors for a search space.
    Requires CONNECTORS_READ permission.
    """
    try:
        # Check if user has permission to read connectors
        await check_permission(
            db,
            current_user,
            search_space_id,
            "CONNECTORS_READ",
            "You don't have permission to view connectors in this search space",
        )

        query = select(Connector).filter(
            Connector.space_id == search_space_id
        )

        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch connectors: {e!s}",
        ) from e


@router.get(
    "/{connector_id}", response_model=ConnectorRead
)
async def read_connector(
    connector_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get a specific connector by ID.
    Requires CONNECTORS_READ permission.
    """
    try:
        # Get the connector first
        result = await db.execute(
            select(Connector).filter(
                Connector.id == connector_id
            )
        )
        connector = result.scalars().first()

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        # Check permission
        await check_permission(
            db,
            current_user,
            connector.space_id,
            "CONNECTORS_READ",
            "You don't have permission to view this connector",
        )

        return connector
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch connector: {e!s}"
        ) from e


@router.put(
    "/{connector_id}", response_model=ConnectorRead
)
async def update_connector(
    connector_id: int,
    connector_update: ConnectorUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Update a connector.
    Requires CONNECTORS_UPDATE permission.
    Handles partial updates, including merging changes into the 'config' field.
    """
    # Get the connector first
    result = await db.execute(
        select(Connector).filter(Connector.id == connector_id)
    )
    db_connector = result.scalars().first()

    if not db_connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Check permission
    await check_permission(
        db,
        current_user,
        db_connector.space_id,
        "CONNECTORS_UPDATE",
        "You don't have permission to update this connector",
    )

    # Convert the sparse update data (only fields present in request) to a dict
    update_data = connector_update.model_dump(exclude_unset=True)

    # Validate periodic indexing fields
    # Get the effective values after update
    effective_is_indexable = update_data.get("is_indexable", db_connector.is_indexable)
    effective_periodic_enabled = update_data.get(
        "periodic_indexing_enabled", db_connector.periodic_indexing_enabled
    )
    effective_frequency = update_data.get(
        "indexing_frequency_minutes", db_connector.indexing_frequency_minutes
    )

    # Validate periodic indexing configuration
    if effective_periodic_enabled:
        if not effective_is_indexable:
            raise HTTPException(
                status_code=422,
                detail="periodic_indexing_enabled can only be True for indexable connectors",
            )
        if effective_frequency is None:
            raise HTTPException(
                status_code=422,
                detail="indexing_frequency_minutes is required when periodic_indexing_enabled is True",
            )
        if effective_frequency <= 0:
            raise HTTPException(
                status_code=422,
                detail="indexing_frequency_minutes must be greater than 0",
            )

        # Automatically set next_scheduled_at if not provided and periodic indexing is being enabled
        if (
            "periodic_indexing_enabled" in update_data
            or "indexing_frequency_minutes" in update_data
        ) and "next_scheduled_at" not in update_data:
            # Schedule the next indexing based on the frequency
            update_data["next_scheduled_at"] = datetime.now(UTC) + timedelta(
                minutes=effective_frequency
            )
    elif (
        effective_periodic_enabled is False
        and "periodic_indexing_enabled" in update_data
    ):
        # If disabling periodic indexing, clear the next_scheduled_at
        update_data["next_scheduled_at"] = None

    # Special handling for 'config' field
    if "config" in update_data:
        incoming_config = update_data["config"]  # Config data from the request
        existing_config = (
            db_connector.config if db_connector.config else {}
        )  # Current config from DB

        # Merge incoming config into existing config
        # This preserves existing keys (like GITHUB_PAT) if they are not in the incoming data
        merged_config = existing_config.copy()
        merged_config.update(incoming_config)

        # -- Validation after merging --
        # Validate the *merged* config based on the connector type
        # We need the connector type - use the one from the update if provided, else the existing one
        current_connector_type = (
            connector_update.connector_type
            if connector_update.connector_type is not None
            else db_connector.connector_type
        )

        try:
            # We can reuse the base validator by creating a temporary base model instance
            # Note: This assumes 'name' and 'is_indexable' are not crucial for config validation itself
            temp_data_for_validation = {
                "name": db_connector.name,  # Use existing name
                "connector_type": current_connector_type,
                "is_indexable": db_connector.is_indexable,  # Use existing value
                "last_indexed_at": db_connector.last_indexed_at,  # Not used by validator
                "config": merged_config,
            }
            ConnectorBase.model_validate(temp_data_for_validation)
        except ValidationError as e:
            # Raise specific validation error for the merged config
            raise HTTPException(
                status_code=422, detail=f"Validation error for merged config: {e!s}"
            ) from e

        # If validation passes, update the main update_data dict with the merged config
        update_data["config"] = merged_config

    # Apply all updates (including the potentially merged config)
    for key, value in update_data.items():
        # Prevent changing connector_type if it causes a duplicate (check moved here)
        if key == "connector_type" and value != db_connector.connector_type:
            check_result = await db.execute(
                select(Connector).filter(
                    Connector.space_id == db_connector.space_id,
                    Connector.connector_type == value,
                    Connector.id != connector_id,
                )
            )
            existing_connector = check_result.scalars().first()
            if existing_connector:
                raise HTTPException(
                    status_code=409,
                    detail=f"A connector with type {value} already exists in this search space.",
                )

        setattr(db_connector, key, value)

    try:
        await db.commit()
        await db.refresh(db_connector)

        # Handle periodic schedule updates
        if (
            "periodic_indexing_enabled" in update_data
            or "indexing_frequency_minutes" in update_data
        ):
            if (
                db_connector.periodic_indexing_enabled
                and db_connector.indexing_frequency_minutes
            ):
                # Create or update the periodic schedule
                success = update_periodic_schedule(
                    connector_id=db_connector.id,
                    search_space_id=db_connector.space_id,
                    user_id=str(current_user.id),
                    connector_type=db_connector.connector_type,
                    frequency_minutes=db_connector.indexing_frequency_minutes,
                )
                if not success:
                    logger.warning(
                        f"Failed to update periodic schedule for connector {db_connector.id}"
                    )
            else:
                # Delete the periodic schedule if disabled
                success = delete_periodic_schedule(db_connector.id)
                if not success:
                    logger.warning(
                        f"Failed to delete periodic schedule for connector {db_connector.id}"
                    )

        return db_connector
    except IntegrityError as e:
        await db.rollback()
        # This might occur if connector_type constraint is violated somehow after the check
        raise HTTPException(
            status_code=409, detail=f"Database integrity error during update: {e!s}"
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Failed to update connector {connector_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update connector: {e!s}",
        ) from e


@router.delete("/{connector_id}", response_model=dict)
async def delete_connector(
    connector_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Delete a connector.
    Requires CONNECTORS_DELETE permission.
    """
    try:
        # Get the connector first
        result = await db.execute(
            select(Connector).filter(
                Connector.id == connector_id
            )
        )
        db_connector = result.scalars().first()

        if not db_connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        # Check permission
        await check_permission(
            db,
            current_user,
            db_connector.space_id,
            "CONNECTORS_DELETE",
            "You don't have permission to delete this connector",
        )

        # Delete any periodic schedule associated with this connector
        if db_connector.periodic_indexing_enabled:
            success = delete_periodic_schedule(connector_id)
            if not success:
                logger.warning(
                    f"Failed to delete periodic schedule for connector {connector_id}"
                )

        await db.delete(db_connector)
        await db.commit()
        return {"message": "Connector deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete connector: {e!s}",
        ) from e


@router.post(
    "/{connector_id}/index", response_model=dict[str, Any]
)
async def index_connector_content(
    connector_id: int,
    start_date: str = Query(
        None,
        description="Start date for indexing (YYYY-MM-DD format). If not provided, uses last_indexed_at or defaults to 365 days ago",
    ),
    end_date: str = Query(
        None,
        description="End date for indexing (YYYY-MM-DD format). If not provided, uses today's date",
    ),
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Index content from a connector to a search space.
    Requires CONNECTORS_UPDATE permission (to trigger indexing).

    Currently supports:
    - SLACK_CONNECTOR: Indexes messages from all accessible Slack channels
    - NOTION_CONNECTOR: Indexes pages from all accessible Notion pages
    - GITHUB_CONNECTOR: Indexes code and documentation from GitHub repositories
    - LINEAR_CONNECTOR: Indexes issues and comments from Linear
    - JIRA_CONNECTOR: Indexes issues and comments from Jira
    - DISCORD_CONNECTOR: Indexes messages from all accessible Discord channels
    - LUMA_CONNECTOR: Indexes events from Luma
    - ELASTICSEARCH_CONNECTOR: Indexes documents from Elasticsearch
    - WEBCRAWLER_CONNECTOR: Indexes web pages from crawled websites

    Args:
        connector_id: ID of the connector to use

    Returns:
        Dictionary with indexing status
    """
    try:
        # Get the connector first
        result = await db.execute(
            select(Connector).filter(
                Connector.id == connector_id
            )
        )
        connector = result.scalars().first()

        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")

        # Get search_space_id from the connector
        search_space_id = connector.space_id

        # Check if user has permission to update connectors (indexing is an update operation)
        await check_permission(
            db,
            current_user,
            search_space_id,
            "CONNECTORS_UPDATE",
            "You don't have permission to index content in this search space",
        )

        # Handle different connector types
        response_message = ""
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Determine the actual date range to use
        if start_date is None:
            # Use last_indexed_at or default to 365 days ago
            if connector.last_indexed_at:
                today = datetime.now().date()
                if connector.last_indexed_at.date() == today:
                    # If last indexed today, go back 1 day to ensure we don't miss anything
                    indexing_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    indexing_from = connector.last_indexed_at.strftime("%Y-%m-%d")
            else:
                indexing_from = (datetime.now() - timedelta(days=365)).strftime(
                    "%Y-%m-%d"
                )
        else:
            indexing_from = start_date

        indexing_to = end_date if end_date else today_str

        if connector.connector_type == ConnectorType.SLACK_CONNECTOR:
            logger.info(
                f"Triggering Slack indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_slack_messages_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Slack indexing started in the background."

        elif connector.connector_type == ConnectorType.NOTION_CONNECTOR:
            logger.info(
                f"Triggering Notion indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_notion_pages_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Notion indexing started in the background."

        elif connector.connector_type == ConnectorType.GITHUB_CONNECTOR:
            logger.info(
                f"Triggering GitHub indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_github_repos_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "GitHub indexing started in the background."

        elif connector.connector_type == ConnectorType.LINEAR_CONNECTOR:
            logger.info(
                f"Triggering Linear indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_linear_issues_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Linear indexing started in the background."

        elif connector.connector_type == ConnectorType.JIRA_CONNECTOR:
            logger.info(
                f"Triggering Jira indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_jira_issues_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Jira indexing started in the background."

        elif connector.connector_type == ConnectorType.CONFLUENCE_CONNECTOR:
            logger.info(
                f"Triggering Confluence indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_confluence_pages_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Confluence indexing started in the background."

        elif connector.connector_type == ConnectorType.BOOKSTACK_CONNECTOR:
            logger.info(
                f"Triggering BookStack indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_bookstack_pages_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "BookStack indexing started in the background."

        elif connector.connector_type == ConnectorType.CLICKUP_CONNECTOR:
            logger.info(
                f"Triggering ClickUp indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_clickup_tasks_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "ClickUp indexing started in the background."

        elif (
            connector.connector_type
            == ConnectorType.GOOGLE_CALENDAR_CONNECTOR
        ):
            logger.info(
                f"Triggering Google Calendar indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_google_calendar_events_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Google Calendar indexing started in the background."
        elif connector.connector_type == ConnectorType.AIRTABLE_CONNECTOR:
            logger.info(
                f"Triggering Airtable indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_airtable_records_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Airtable indexing started in the background."
        elif (
            connector.connector_type == ConnectorType.GOOGLE_GMAIL_CONNECTOR
        ):
            logger.info(
                f"Triggering Google Gmail indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_google_gmail_messages_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Google Gmail indexing started in the background."

        elif connector.connector_type == ConnectorType.DISCORD_CONNECTOR:
            logger.info(
                f"Triggering Discord indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_discord_messages_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Discord indexing started in the background."

        elif connector.connector_type == ConnectorType.LUMA_CONNECTOR:
            logger.info(
                f"Triggering Luma indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_luma_events_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Luma indexing started in the background."

        elif (
            connector.connector_type
            == ConnectorType.ELASTICSEARCH_CONNECTOR
        ):
            logger.info(
                f"Triggering Elasticsearch indexing for connector {connector_id} into search space {search_space_id}"
            )
            index_elasticsearch_documents_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Elasticsearch indexing started in the background."

        elif connector.connector_type == ConnectorType.WEBCRAWLER_CONNECTOR:
            logger.info(
                f"Triggering web pages indexing for connector {connector_id} into search space {search_space_id} from {indexing_from} to {indexing_to}"
            )
            index_crawled_urls_task.delay(
                connector_id, search_space_id, str(current_user.id), indexing_from, indexing_to
            )
            response_message = "Web page indexing started in the background."

        else:
            # For connector types without specific indexing implementation,
            # return success but indicate no automatic indexing is available
            response_message = f"Connector type '{connector.connector_type}' does not have automatic indexing implemented. Manual document upload or custom integration required."
            logger.info(
                f"Indexing endpoint called for unsupported connector type: {connector.connector_type} (connector_id={connector_id})"
            )

        return {
            "message": response_message,
            "connector_id": connector_id,
            "search_space_id": search_space_id,
            "indexing_from": indexing_from,
            "indexing_to": indexing_to,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to initiate indexing for connector {connector_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate indexing: {e!s}"
        ) from e
