"""Connector incremental sync tasks.

This module provides background tasks for syncing connectors with external data sources:
- Periodic sync for all enabled connectors
- Individual connector sync
- Change detection and processing
- Automatic document upload and indexing
"""

import hashlib
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from langflow.core.celery_app import celery_app
from langflow.services.database.models.connector.model import Connector
from langflow.services.database.models.document.model import Document

logger = logging.getLogger(__name__)


@celery_app.task(name="langflow.workers.sync_connector", bind=True)
def sync_connector_task(self, connector_id: int):
    """Sync a single connector with its external data source.

    This task:
    1. Fetches changed files since last_indexed_at
    2. Uploads new/modified files to data-construction
    3. Creates Document records
    4. Triggers ETL processing
    5. Deletes removed files
    6. Updates connector statistics

    Args:
        connector_id: ID of the connector to sync

    Returns:
        dict: Sync statistics
    """
    import asyncio

    from langflow.services.deps import get_session

    async def _sync_connector():
        """Async implementation of connector sync."""
        async with get_session() as session:
            # Get connector
            result = await session.execute(
                select(Connector).where(Connector.id == connector_id)
            )
            connector = result.scalar_one_or_none()

            if not connector:
                logger.error(f"Connector {connector_id} not found")
                return {"success": False, "error": "Connector not found"}

            if not connector.is_enabled:
                logger.info(f"Connector {connector_id} is disabled, skipping sync")
                return {"success": False, "error": "Connector disabled"}

            logger.info(
                f"Starting sync for connector {connector_id} ({connector.connector_type})"
            )

            # Update status
            connector.indexing_status = "running"
            await session.commit()

            try:
                # Get last sync time (use connector creation time if never synced)
                last_sync = connector.last_indexed_at or connector.created_at

                # Sync based on connector type
                stats = await _sync_connector_files(
                    connector=connector, last_sync=last_sync, session=session
                )

                # Update connector
                connector.indexing_status = "idle"
                connector.last_indexed_at = datetime.utcnow()
                connector.indexed_file_count = stats.get("total_files", 0)

                # Schedule next sync if periodic indexing enabled
                if connector.periodic_indexing_enabled and connector.indexing_frequency_minutes:
                    connector.next_scheduled_at = datetime.utcnow() + timedelta(
                        minutes=connector.indexing_frequency_minutes
                    )

                await session.commit()

                logger.info(
                    f"Connector {connector_id} sync completed: {stats.get('new_files', 0)} new, "
                    f"{stats.get('modified_files', 0)} modified, {stats.get('deleted_files', 0)} deleted"
                )

                return {"success": True, **stats}

            except Exception as e:
                logger.error(f"Connector {connector_id} sync failed: {e}", exc_info=True)

                # Update status
                connector.indexing_status = "failed"
                await session.commit()

                return {"success": False, "error": str(e)}

    # Run async function
    return asyncio.run(_sync_connector())


async def _sync_connector_files(
    connector: Connector, last_sync: datetime, session
) -> dict:
    """Sync files for a specific connector type.

    Args:
        connector: Connector instance
        last_sync: Last sync timestamp
        session: Database session

    Returns:
        dict: Statistics about the sync
    """
    from lfx.services.feign.clients.data_construction import DataConstructionFeignClient
    from lfx.services.feign.service import get_feign_service

    stats = {
        "new_files": 0,
        "modified_files": 0,
        "deleted_files": 0,
        "total_files": 0,
        "errors": 0,
    }

    # Get connector service
    from langflow.connectors.service import ConnectorService

    connector_service = ConnectorService(session, search_space_id=connector.space_id)

    # Get data-construction client
    feign_service = get_feign_service()
    dc_client = DataConstructionFeignClient(feign_service)

    # Map connector type to service method
    connector_type_map = {
        "NOTION": "get_notion_changes",
        "GITHUB": "get_github_changes",
        "GOOGLE_DRIVE": "get_google_drive_changes",
        "CONFLUENCE": "get_confluence_changes",
        "SLACK": "get_slack_changes",
        # Add more mappings as needed
    }

    method_name = connector_type_map.get(connector.connector_type)
    if not method_name:
        logger.warning(
            f"Connector type {connector.connector_type} not supported for incremental sync"
        )
        return stats

    # Get changes from connector (this would call the actual connector API)
    # For now, this is a placeholder - actual implementation depends on connector SDK
    try:
        # Example: changes = await connector_service.{method_name}(
        #     connector_id=connector.id,
        #     since=last_sync
        # )
        changes = []  # Placeholder

        for change in changes:
            try:
                if change["type"] in ["added", "modified"]:
                    # Process new or modified file
                    await _process_connector_file(
                        connector=connector,
                        change=change,
                        dc_client=dc_client,
                        session=session,
                    )

                    if change["type"] == "added":
                        stats["new_files"] += 1
                    else:
                        stats["modified_files"] += 1

                elif change["type"] == "deleted":
                    # Delete document
                    await _delete_connector_file(
                        connector=connector, change=change, session=session
                    )
                    stats["deleted_files"] += 1

            except Exception as e:
                logger.error(
                    f"Error processing change {change.get('file_id')}: {e}", exc_info=True
                )
                stats["errors"] += 1

        # Get total file count
        stats["total_files"] = await _count_connector_documents(connector.id, session)

    except Exception as e:
        logger.error(f"Error getting changes for connector {connector.id}: {e}", exc_info=True)
        stats["errors"] += 1

    return stats


async def _process_connector_file(
    connector: Connector, change: dict, dc_client, session
):
    """Process a new or modified file from connector.

    Args:
        connector: Connector instance
        change: Change information from connector
        dc_client: DataConstructionFeignClient instance
        session: Database session
    """
    # Download file from connector (placeholder - actual implementation depends on connector SDK)
    # file_content = await connector_service.download_file(change['file_id'])
    file_content = b""  # Placeholder
    filename = change.get("filename", "unknown")

    # Calculate content hash for deduplication
    content_hash = hashlib.sha256(file_content).hexdigest()

    # Check if document already exists
    result = await session.execute(
        select(Document).where(
            Document.content_hash == content_hash,
            Document.connector_id == connector.id,
        )
    )
    existing_doc = result.scalar_one_or_none()

    if existing_doc:
        # Update existing document
        existing_doc.processing_status = "pending"
        existing_doc.updated_at = datetime.utcnow()
        await session.commit()

        # Trigger reprocessing
        from langflow.tasks.document_tasks import process_document_pipeline_task

        process_document_pipeline_task.delay(existing_doc.id)

        logger.info(f"Updated existing document {existing_doc.id} from connector {connector.id}")
    else:
        # Upload to data-construction
        if not connector.data_construction_folder_id:
            logger.error(
                f"Connector {connector.id} has no data_construction_folder_id configured"
            )
            return

        dc_file = await dc_client.upload_file(
            folder_id=connector.data_construction_folder_id,
            file_content=file_content,
            filename=filename,
        )

        # Create new document
        document = Document(
            title=filename,
            content="",
            content_hash=content_hash,
            file_name=filename,
            file_type=change.get("file_type"),
            file_size=len(file_content),
            data_construction_file_id=dc_file["id"],
            data_construction_folder_id=connector.data_construction_folder_id,
            space_id=connector.space_id,
            connector_id=connector.id,
            processing_status="pending",
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)

        # Trigger processing
        from langflow.tasks.document_tasks import process_document_pipeline_task

        process_document_pipeline_task.delay(document.id)

        logger.info(f"Created new document {document.id} from connector {connector.id}")


async def _delete_connector_file(connector: Connector, change: dict, session):
    """Delete a file that was removed from connector.

    Args:
        connector: Connector instance
        change: Change information
        session: Database session
    """
    # Find document by external_id (would need to add this field to Document model)
    # For now, skip deletion as we don't have external_id tracking
    logger.warning(
        f"File deletion not implemented yet for connector {connector.id}, "
        f"file: {change.get('file_id')}"
    )


async def _count_connector_documents(connector_id: int, session) -> int:
    """Count total documents for a connector.

    Args:
        connector_id: Connector ID
        session: Database session

    Returns:
        int: Number of documents
    """
    from sqlalchemy import func

    result = await session.execute(
        select(func.count(Document.id)).where(Document.connector_id == connector_id)
    )
    return result.scalar() or 0


@celery_app.task(name="langflow.workers.sync_all_connectors")
def sync_all_connectors_task():
    """Sync all connectors that are due for sync.

    This task:
    1. Finds all connectors with periodic_indexing_enabled=True
    2. Checks if they are due for sync (next_scheduled_at <= now)
    3. Triggers sync for each due connector

    Returns:
        dict: Summary of connectors synced
    """
    import asyncio

    from langflow.services.deps import get_session

    async def _sync_all():
        """Async implementation of sync all connectors."""
        async with get_session() as session:
            # Find connectors due for sync
            now = datetime.utcnow()
            result = await session.execute(
                select(Connector).where(
                    Connector.periodic_indexing_enabled == True,  # noqa: E712
                    Connector.is_enabled == True,  # noqa: E712
                    Connector.indexing_status != "running",
                    # Either never synced OR next_scheduled_at is in the past
                    (
                        (Connector.next_scheduled_at.is_(None))
                        | (Connector.next_scheduled_at <= now)
                    ),
                )
            )
            connectors = result.scalars().all()

            logger.info(f"Found {len(connectors)} connectors due for sync")

            synced = 0
            skipped = 0

            for connector in connectors:
                try:
                    # Trigger sync task
                    sync_connector_task.delay(connector.id)
                    synced += 1
                    logger.info(f"Triggered sync for connector {connector.id} ({connector.name})")
                except Exception as e:
                    logger.error(
                        f"Failed to trigger sync for connector {connector.id}: {e}",
                        exc_info=True,
                    )
                    skipped += 1

            return {"synced": synced, "skipped": skipped, "total": len(connectors)}

    return asyncio.run(_sync_all())
