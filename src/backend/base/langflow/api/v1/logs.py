from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import and_, desc
from sqlalchemy.future import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.log import Log, LogCreate, LogLevel, LogRead, LogStatus, LogUpdate
from langflow.services.database.models.role import Permission
from langflow.services.database.models.space import Space
from langflow.services.database.models.space_membership import SpaceMembership
from langflow.services.database.models.user import User
from langflow.utils.rbac import check_permission

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.post("/logs", response_model=LogRead)
async def create_log(
    log: LogCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Create a new log entry.
    Note: This is typically called internally. Requires LOGS_READ permission (since logs are usually system-generated).
    """
    try:
        # Check if the user has access to the search space
        await check_permission(
            db,
            current_user,
            log.search_space_id,
            Permission.LOGS_READ.value,
            "You don't have permission to access logs in this search space",
        )

        db_log = Log(**log.model_dump())
        db.add(db_log)
        await db.commit()
        await db.refresh(db_log)
        return db_log
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create log: {e!s}"
        ) from e


@router.get("/logs", response_model=list[LogRead])
async def read_logs(
    skip: int = 0,
    limit: int = 100,
    search_space_id: int | None = None,
    level: LogLevel | None = None,
    status: LogStatus | None = None,
    source: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Get logs with optional filtering.
    Requires LOGS_READ permission for the search space(s).
    """
    try:
        # Apply filters
        filters = []

        if search_space_id is not None:
            # Check permission for specific search space
            await check_permission(
                db,
                current_user,
                search_space_id,
                Permission.LOGS_READ.value,
                "You don't have permission to read logs in this search space",
            )
            # Build query for specific search space
            query = (
                select(Log)
                .filter(Log.search_space_id == search_space_id)
                .order_by(desc(Log.created_at))
            )
        else:
            # Build base query - logs from search spaces user has membership in
            query = (
                select(Log)
                .join(Space)
                .join(SpaceMembership)
                .filter(SpaceMembership.user_id == current_user.id)
                .order_by(desc(Log.created_at))
            )

        if level is not None:
            filters.append(Log.level == level)

        if status is not None:
            filters.append(Log.status == status)

        if source is not None:
            filters.append(Log.source.ilike(f"%{source}%"))

        if start_date is not None:
            filters.append(Log.created_at >= start_date)

        if end_date is not None:
            filters.append(Log.created_at <= end_date)

        if filters:
            query = query.filter(and_(*filters))

        # Apply pagination
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch logs: {e!s}"
        ) from e


@router.get("/logs/{log_id}", response_model=LogRead)
async def read_log(
    log_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Get a specific log by ID.
    Requires LOGS_READ permission for the search space.
    """
    try:
        result = await db.execute(select(Log).filter(Log.id == log_id))
        log = result.scalars().first()

        if not log:
            raise HTTPException(status_code=404, detail="Log not found")

        # Check permission for the search space
        await check_permission(
            db,
            current_user,
            log.search_space_id,
            Permission.LOGS_READ.value,
            "You don't have permission to read logs in this search space",
        )

        return log
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch log: {e!s}"
        ) from e


@router.put("/logs/{log_id}", response_model=LogRead)
async def update_log(
    log_id: int,
    log_update: LogUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Update a log entry.
    Requires LOGS_READ permission (logs are typically updated by system).
    """
    try:
        result = await db.execute(select(Log).filter(Log.id == log_id))
        db_log = result.scalars().first()

        if not db_log:
            raise HTTPException(status_code=404, detail="Log not found")

        # Check permission for the search space
        await check_permission(
            db,
            current_user,
            db_log.search_space_id,
            Permission.LOGS_READ.value,
            "You don't have permission to access logs in this search space",
        )

        # Update only provided fields
        update_data = log_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_log, field, value)

        await db.commit()
        await db.refresh(db_log)
        return db_log
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update log: {e!s}"
        ) from e


@router.delete("/logs/{log_id}")
async def delete_log(
    log_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Delete a log entry.
    Requires LOGS_DELETE permission for the search space.
    """
    try:
        result = await db.execute(select(Log).filter(Log.id == log_id))
        db_log = result.scalars().first()

        if not db_log:
            raise HTTPException(status_code=404, detail="Log not found")

        # Check permission for the search space
        await check_permission(
            db,
            current_user,
            db_log.search_space_id,
            Permission.LOGS_DELETE.value,
            "You don't have permission to delete logs in this search space",
        )

        await db.delete(db_log)
        await db.commit()
        return {"message": "Log deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete log: {e!s}"
        ) from e


@router.get("/logs/search-space/{search_space_id}/summary")
async def get_logs_summary(
    search_space_id: int,
    hours: int = 24,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Get a summary of logs for a search space in the last X hours.
    Requires LOGS_READ permission for the search space.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.LOGS_READ.value,
            "You don't have permission to read logs in this search space",
        )

        # Calculate time window
        since = datetime.utcnow().replace(microsecond=0) - timedelta(hours=hours)

        # Get logs from the time window
        result = await db.execute(
            select(Log)
            .filter(
                and_(Log.search_space_id == search_space_id, Log.created_at >= since)
            )
            .order_by(desc(Log.created_at))
        )
        logs = result.scalars().all()

        # Create summary
        summary = {
            "total_logs": len(logs),
            "time_window_hours": hours,
            "by_status": {},
            "by_level": {},
            "by_source": {},
            "active_tasks": [],
            "recent_failures": [],
        }

        # Count by status and level
        for log in logs:
            # Status counts
            status_str = log.status.value
            summary["by_status"][status_str] = (
                summary["by_status"].get(status_str, 0) + 1
            )

            # Level counts
            level_str = log.level.value
            summary["by_level"][level_str] = summary["by_level"].get(level_str, 0) + 1

            # Source counts
            if log.source:
                summary["by_source"][log.source] = (
                    summary["by_source"].get(log.source, 0) + 1
                )

            # Active tasks (IN_PROGRESS)
            if log.status == LogStatus.IN_PROGRESS:
                task_name = (
                    log.log_metadata.get("task_name", "Unknown")
                    if log.log_metadata
                    else "Unknown"
                )
                summary["active_tasks"].append(
                    {
                        "id": log.id,
                        "task_name": task_name,
                        "message": log.message,
                        "started_at": log.created_at,
                        "source": log.source,
                    }
                )

            # Recent failures
            if log.status == LogStatus.FAILED and len(summary["recent_failures"]) < 10:
                task_name = (
                    log.log_metadata.get("task_name", "Unknown")
                    if log.log_metadata
                    else "Unknown"
                )
                summary["recent_failures"].append(
                    {
                        "id": log.id,
                        "task_name": task_name,
                        "message": log.message,
                        "failed_at": log.created_at,
                        "source": log.source,
                        "error_details": log.log_metadata.get("error_details")
                        if log.log_metadata
                        else None,
                    }
                )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate logs summary: {e!s}"
        ) from e
