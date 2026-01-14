"""Compatibility wrapper for task_logging_service imports.

This module provides backward compatibility for SurfSense-style imports.
New code should import directly from langflow.services.task_logging.service instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langflow.services.database.models import Log

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.database.models.log import LogLevel


class TaskLoggingService:
    """Compatibility wrapper for TaskLoggingService with SurfSense-style API.

    This wrapper accepts (session, space_id) in the constructor to maintain
    backward compatibility with SurfSense code, where session is stored as
    an instance variable rather than passed to each method.

    New code should use langflow.services.task_logging.service.TaskLoggingService directly.
    """

    def __init__(self, session: AsyncSession, space_id: int):
        """Initialize TaskLoggingService wrapper.

        Args:
            session: Database session (stored for use in methods)
            space_id: Space ID (stored for use in methods)
        """
        self.session = session
        self.space_id = space_id

    async def log_task_start(
        self,
        task_name: str,
        source: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Log the start of a task with IN_PROGRESS status.

        Args:
            task_name: Name/identifier of the task
            source: Source service/component
            message: Human-readable message about the task
            metadata: Additional context data

        Returns:
            The created log entry
        """
        from langflow.services.deps import get_task_logging_service

        task_logging_service = get_task_logging_service()
        return await task_logging_service.log_task_start(
            session=self.session,
            space_id=self.space_id,
            task_name=task_name,
            source=source,
            message=message,
            metadata=metadata,
        )

    async def log_task_success(
        self,
        log_entry: Log,
        message: str,
        additional_metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Update a log entry to SUCCESS status.

        Args:
            log_entry: The original log entry to update
            message: Success message
            additional_metadata: Additional metadata to merge

        Returns:
            The updated log entry
        """
        from langflow.services.deps import get_task_logging_service

        task_logging_service = get_task_logging_service()
        return await task_logging_service.log_task_success(
            session=self.session,
            log_entry=log_entry,
            message=message,
            additional_metadata=additional_metadata,
        )

    async def log_task_failure(
        self,
        log_entry: Log,
        error_message: str,
        error_details: str | None = None,
        additional_metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Update a log entry to FAILED status.

        Args:
            log_entry: The original log entry to update
            error_message: Error message
            error_details: Detailed error information
            additional_metadata: Additional metadata to merge

        Returns:
            The updated log entry
        """
        from langflow.services.deps import get_task_logging_service

        task_logging_service = get_task_logging_service()
        return await task_logging_service.log_task_failure(
            session=self.session,
            log_entry=log_entry,
            error_message=error_message,
            error_details=error_details,
            additional_metadata=additional_metadata,
        )

    async def log_task_progress(
        self,
        log_entry: Log,
        progress_message: str,
        progress_metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Update a log entry with progress information.

        Args:
            log_entry: The log entry to update
            progress_message: Progress update message
            progress_metadata: Additional progress metadata

        Returns:
            The updated log entry
        """
        from langflow.services.deps import get_task_logging_service

        task_logging_service = get_task_logging_service()
        return await task_logging_service.log_task_progress(
            session=self.session,
            log_entry=log_entry,
            progress_message=progress_message,
            progress_metadata=progress_metadata,
        )

    async def log_simple_event(
        self,
        level: LogLevel,
        source: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> Log:
        """Log a simple event (not a long-running task).

        Args:
            level: Log level
            source: Source service/component
            message: Log message
            metadata: Additional context data

        Returns:
            The created log entry
        """
        from langflow.services.deps import get_task_logging_service

        task_logging_service = get_task_logging_service()
        return await task_logging_service.log_simple_event(
            session=self.session,
            space_id=self.space_id,
            level=level,
            source=source,
            message=message,
            metadata=metadata,
        )


__all__ = ["TaskLoggingService"]
