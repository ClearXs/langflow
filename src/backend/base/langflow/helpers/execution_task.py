"""Helper functions for managing execution tasks."""

from uuid import UUID

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.task import TaskTable
from langflow.services.execution_task.service import ExecutionTaskService


async def create_execution_task(
    session: AsyncSession,
    flow_id: UUID,
    run_id: str,
    user_id: UUID | None = None,
    trigger_type: str = "manual",
) -> TaskTable | None:
    """Create an execution task for a flow run.

    Args:
        session: Database session
        flow_id: Flow UUID
        run_id: Run identifier
        user_id: User UUID
        trigger_type: Trigger type

    Returns:
        TaskTable | None: Created task or None if creation failed
    """
    try:
        task_service = ExecutionTaskService(session)
        task = await task_service.create_task(
            flow_id=flow_id, run_id=run_id, user_id=user_id, trigger_type=trigger_type
        )
        return task
    except Exception as e:
        logger.exception(f"Failed to create execution task: {e}")
        return None


async def update_execution_task(session: AsyncSession, run_id: str) -> TaskTable | None:
    """Update an execution task from its transactions.

    Args:
        session: Database session
        run_id: Run identifier

    Returns:
        TaskTable | None: Updated task or None if update failed
    """
    try:
        task_service = ExecutionTaskService(session)
        task = await task_service.update_task_from_transactions(run_id)
        return task
    except Exception as e:
        logger.exception(f"Failed to update execution task: {e}")
        return None
