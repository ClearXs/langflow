"""API endpoints for managing flow execution tasks."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from langflow.services.auth.utils import get_current_active_user
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.task import TaskTable
from langflow.services.database.models.user.model import User
from langflow.services.deps import get_session
from langflow.services.execution_task.service import ExecutionTaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskListResponse(BaseModel):
    """Response model for task list."""

    total: int
    tasks: list[TaskTable]


class TaskDetailResponse(BaseModel):
    """Response model for task detail."""

    task: TaskTable
    transactions: list[dict]
    data_exchanges: list[dict]


@router.get("/flows/{flow_id}/tasks")
async def get_flow_tasks(
    flow_id: UUID,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
) -> TaskListResponse:
    """Get all tasks for a flow.

    Args:
        flow_id: Flow UUID
        status: Optional status filter ("running" | "success" | "error")
        start_date: Optional start date filter (ISO format: YYYY-MM-DD)
        end_date: Optional end date filter (ISO format: YYYY-MM-DD)
        limit: Maximum number of tasks to return (default: 50)
        offset: Number of tasks to skip (default: 0)
        session: Database session
        current_user: Current authenticated user

    Returns:
        TaskListResponse: List of tasks with total count

    Raises:
        HTTPException: 404 if flow not found, 403 if unauthorized
    """
    # Verify flow exists and user has access
    stmt = select(Flow).where(Flow.id == flow_id)
    if current_user:
        stmt = stmt.where(Flow.user_id == current_user.id)

    result = await session.exec(stmt)
    flow = result.first()

    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow {flow_id} not found or access denied",
        )

    # Get tasks
    task_service = ExecutionTaskService(session)
    tasks, total = await task_service.get_tasks_by_flow(
        flow_id=flow_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return TaskListResponse(total=total, tasks=tasks)


@router.get("/{task_id}")
async def get_task_detail(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
) -> dict:
    """Get detailed information about a task.

    Args:
        task_id: Task UUID
        session: Database session
        current_user: Current authenticated user

    Returns:
        dict: Task detail with transactions and data exchanges

    Raises:
        HTTPException: 404 if task not found, 403 if unauthorized
    """
    task_service = ExecutionTaskService(session)
    task_detail = await task_service.get_task_detail(task_id)

    if not task_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Verify user has access to the flow
    task = task_detail["task"]
    if current_user:
        stmt = select(Flow).where(Flow.id == task.flow_id).where(Flow.user_id == current_user.id)
        result = await session.exec(stmt)
        flow = result.first()

        if not flow:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this task",
            )

    # Convert SQLModel objects to dicts for JSON serialization
    return {
        "task": task.model_dump() if hasattr(task, "model_dump") else dict(task),
        "transactions": [
            tx.model_dump() if hasattr(tx, "model_dump") else dict(tx) for tx in task_detail["transactions"]
        ],
        "data_exchanges": [
            ex.model_dump() if hasattr(ex, "model_dump") else dict(ex) for ex in task_detail["data_exchanges"]
        ],
    }


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
) -> dict:
    """Delete a task.

    Args:
        task_id: Task UUID
        session: Database session
        current_user: Current authenticated user

    Returns:
        dict: Success message

    Raises:
        HTTPException: 404 if task not found, 403 if unauthorized
    """
    task_service = ExecutionTaskService(session)

    # Get task first to verify access
    task = await task_service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Verify user has access to the flow
    if current_user:
        stmt = select(Flow).where(Flow.id == task.flow_id).where(Flow.user_id == current_user.id)
        result = await session.exec(stmt)
        flow = result.first()

        if not flow:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this task",
            )

    # Delete the task
    success = await task_service.delete_task(task_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task",
        )

    return {"message": "Task deleted successfully", "task_id": str(task_id)}
