"""TaskLoggingService for logging background tasks and events in Holo knowledge system."""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from langflow.services.base import Service
from langflow.services.database.models import Log, LogLevel, LogStatus

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.settings.service import SettingsService

logger = logging.getLogger(__name__)


def utc_now():
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class TaskLoggingService(Service):
    """Service for logging background tasks using the database Log model.

    This service provides structured logging for:
    - Long-running background tasks (with start, progress, success/failure tracking)
    - Simple events (one-time log entries)
    - Task lifecycle management
    """

    name = "task_logging_service"

    def __init__(self, settings_service: SettingsService):
        """Initialize TaskLoggingService.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self.set_ready()

    async def log_task_start(
        self,
        session: AsyncSession,
        space_id: int,
        task_name: str,
        source: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Log the start of a task with IN_PROGRESS status.

        Args:
            session: Database session
            space_id: Space ID where the task is running
            task_name: Name/identifier of the task
            source: Source service/component (e.g., 'document_processor', 'slack_indexer')
            message: Human-readable message about the task
            metadata: Additional context data

        Returns:
            The created log entry
        """
        log_metadata = metadata or {}
        log_metadata.update({"task_name": task_name, "started_at": utc_now().isoformat()})

        log_entry = Log(
            level=LogLevel.INFO,
            status=LogStatus.IN_PROGRESS,
            message=message,
            source=source,
            log_metadata=log_metadata,
            search_space_id=space_id,
        )

        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)

        logger.info(f"Started task {task_name}: {message}")
        return log_entry

    async def log_task_success(
        self,
        session: AsyncSession,
        log_entry: Log,
        message: str,
        additional_metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Update a log entry to SUCCESS status.

        Args:
            session: Database session
            log_entry: The original log entry to update
            message: Success message
            additional_metadata: Additional metadata to merge

        Returns:
            The updated log entry
        """
        # Ensure session is in a valid state
        if not session.is_active:
            await session.rollback()

        # Refresh log_entry to avoid expired state
        with contextlib.suppress(Exception):
            await session.refresh(log_entry)

        # Update the existing log entry
        log_entry.status = LogStatus.SUCCESS
        log_entry.message = message

        # Merge additional metadata
        if additional_metadata:
            if log_entry.log_metadata is None:
                log_entry.log_metadata = {}
            log_entry.log_metadata.update(additional_metadata)
            log_entry.log_metadata["completed_at"] = utc_now().isoformat()

        await session.commit()
        await session.refresh(log_entry)

        task_name = (
            log_entry.log_metadata.get("task_name", "unknown")
            if log_entry.log_metadata
            else "unknown"
        )
        logger.info(f"Completed task {task_name}: {message}")
        return log_entry

    async def log_task_failure(
        self,
        session: AsyncSession,
        log_entry: Log,
        error_message: str,
        error_details: str | None = None,
        additional_metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Update a log entry to FAILED status.

        Args:
            session: Database session
            log_entry: The original log entry to update
            error_message: Error message
            error_details: Detailed error information
            additional_metadata: Additional metadata to merge

        Returns:
            The updated log entry
        """
        # Ensure session is in a valid state
        if not session.is_active:
            await session.rollback()

        # Refresh log_entry to avoid expired state
        with contextlib.suppress(Exception):
            await session.refresh(log_entry)

        # Update the existing log entry
        log_entry.status = LogStatus.FAILED
        log_entry.level = LogLevel.ERROR
        log_entry.message = error_message

        # Merge additional metadata
        if log_entry.log_metadata is None:
            log_entry.log_metadata = {}

        log_entry.log_metadata.update(
            {"failed_at": utc_now().isoformat(), "error_details": error_details}
        )

        if additional_metadata:
            log_entry.log_metadata.update(additional_metadata)

        await session.commit()
        await session.refresh(log_entry)

        task_name = (
            log_entry.log_metadata.get("task_name", "unknown")
            if log_entry.log_metadata
            else "unknown"
        )
        logger.error(f"Failed task {task_name}: {error_message}")
        if error_details:
            logger.error(f"Error details: {error_details}")

        return log_entry

    async def log_task_progress(
        self,
        session: AsyncSession,
        log_entry: Log,
        progress_message: str,
        progress_metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Update a log entry with progress information while keeping IN_PROGRESS status.

        Args:
            session: Database session
            log_entry: The log entry to update
            progress_message: Progress update message
            progress_metadata: Additional progress metadata

        Returns:
            The updated log entry
        """
        # Ensure session is in a valid state
        if not session.is_active:
            await session.rollback()

        # Refresh log_entry to avoid expired state
        with contextlib.suppress(Exception):
            await session.refresh(log_entry)

        log_entry.message = progress_message

        if progress_metadata:
            if log_entry.log_metadata is None:
                log_entry.log_metadata = {}
            log_entry.log_metadata.update(progress_metadata)
            log_entry.log_metadata["last_progress_update"] = utc_now().isoformat()

        await session.commit()
        await session.refresh(log_entry)

        task_name = (
            log_entry.log_metadata.get("task_name", "unknown")
            if log_entry.log_metadata
            else "unknown"
        )
        logger.info(f"Progress update for task {task_name}: {progress_message}")
        return log_entry

    async def log_simple_event(
        self,
        session: AsyncSession,
        space_id: int,
        level: LogLevel,
        source: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Log a simple event (not a long-running task).

        Args:
            session: Database session
            space_id: Space ID where the event occurred
            level: Log level
            source: Source service/component
            message: Log message
            metadata: Additional context data

        Returns:
            The created log entry
        """
        log_entry = Log(
            level=level,
            status=LogStatus.SUCCESS,  # Simple events are immediately complete
            message=message,
            source=source,
            log_metadata=metadata or {},
            search_space_id=space_id,
        )

        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)

        logger.info(f"Logged event from {source}: {message}")
        return log_entry
