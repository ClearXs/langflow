"""Service for managing flow execution tasks."""

from datetime import datetime, timezone
from uuid import UUID

from lfx.log.logger import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.data_exchange import DataExchangeTable
from langflow.services.database.models.task import TaskTable
from langflow.services.database.models.transactions import TransactionTable


class ExecutionTaskService:
    """Service for managing flow execution tasks.

    A task represents a single execution of a flow, aggregating all component
    executions (transactions) and data exchanges that occurred during that execution.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(
        self,
        flow_id: UUID,
        run_id: str,
        user_id: UUID | None = None,
        trigger_type: str = "manual",
        execution_config: dict | None = None,
    ) -> TaskTable:
        """Create a new task for a flow execution.

        Args:
            flow_id: UUID of the flow being executed
            run_id: Unique run identifier for this execution
            user_id: UUID of the user who triggered the execution
            trigger_type: How the execution was triggered ("manual" | "api" | "webhook")
            execution_config: Optional configuration dict for this execution

        Returns:
            TaskTable: The created task record
        """
        task = TaskTable(
            flow_id=flow_id,
            run_id=run_id,
            user_id=user_id,
            trigger_type=trigger_type,
            execution_config=execution_config,
            status="running",
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)

        logger.debug(f"Created task {task.id} for flow {flow_id} with run_id {run_id}")
        return task

    async def get_task_by_run_id(self, run_id: str) -> TaskTable | None:
        """Get a task by its run_id.

        Args:
            run_id: The run identifier

        Returns:
            TaskTable | None: The task if found, None otherwise
        """
        statement = select(TaskTable).where(TaskTable.run_id == run_id)
        result = await self.session.exec(statement)
        return result.first()

    async def get_task_by_id(self, task_id: UUID) -> TaskTable | None:
        """Get a task by its ID.

        Args:
            task_id: The task UUID

        Returns:
            TaskTable | None: The task if found, None otherwise
        """
        statement = select(TaskTable).where(TaskTable.id == task_id)
        result = await self.session.exec(statement)
        return result.first()

    async def update_task_from_transactions(self, run_id: str) -> TaskTable | None:
        """Update task statistics by aggregating data from all transactions.

        This method:
        1. Fetches all transactions for the given run_id
        2. Aggregates statistics (component counts, data stats, performance)
        3. Determines task status (if any component failed, task fails)
        4. Updates the task record

        Args:
            run_id: The run identifier

        Returns:
            TaskTable | None: The updated task, or None if task not found
        """
        # Get the task
        task = await self.get_task_by_run_id(run_id)
        if not task:
            logger.warning(f"Task not found for run_id {run_id}")
            return None

        # Get all transactions for this run_id directly (much more accurate than time window)
        statement = (
            select(TransactionTable).where(TransactionTable.run_id == run_id).order_by(TransactionTable.timestamp.asc())
        )
        result = await self.session.exec(statement)
        transactions = result.all()

        # Debug: Also check if there are any transactions for this flow without run_id
        debug_statement = select(TransactionTable).where(
            TransactionTable.flow_id == task.flow_id,
            TransactionTable.timestamp >= task.created_at,
        )
        debug_result = await self.session.exec(debug_statement)
        all_flow_transactions = debug_result.all()

        logger.debug(
            f"Transaction query for run_id={run_id}: "
            f"found {len(transactions)} with run_id, "
            f"found {len(all_flow_transactions)} for flow_id={task.flow_id} since task created"
        )

        if len(all_flow_transactions) > len(transactions):
            logger.warning(
                f"Found {len(all_flow_transactions) - len(transactions)} transactions without run_id! "
                f"run_id={run_id}, flow_id={task.flow_id}"
            )

        if not transactions:
            logger.info(
                f"No transactions found for task {task.id}, run_id={run_id}. "
                f"This is normal for empty flows (flows with no components)."
            )
            # 对于空流程，标记为成功并设置所有统计为 0
            task.status = "success"
            task.total_components = 0
            task.success_components = 0
            task.error_components = 0
            task.total_data_rows = 0
            task.total_data_size_mb = 0.0
            task.total_exchanges = 0
            task.total_duration_ms = 0
            task.avg_memory_mb = 0.0

            if not task.started_at:
                task.started_at = task.created_at
            task.completed_at = datetime.now(timezone.utc)

            await self.session.commit()
            await self.session.refresh(task)

            logger.debug(f"Updated empty flow task {task.id} to success status")
            return task

        # Initialize statistics
        total_components = len(transactions)
        success_components = 0
        error_components = 0
        total_data_rows = 0
        total_data_size_mb = 0.0
        total_duration_ms = 0
        total_memory_mb = 0.0
        first_error_component_id = None
        first_error_message = None
        has_running = False
        latest_timestamp = task.created_at

        # Aggregate statistics from transactions
        for tx in transactions:
            # Update timestamp
            latest_timestamp = max(latest_timestamp, tx.timestamp)

            # Count component statuses
            if tx.status == "success":
                success_components += 1
            elif tx.status == "error":
                error_components += 1
                # Capture first error
                if first_error_component_id is None:
                    first_error_component_id = tx.vertex_id
                    first_error_message = tx.error
            elif tx.status == "running":
                has_running = True

            # Extract metadata from outputs
            if tx.outputs and isinstance(tx.outputs, dict):
                metadata = tx.outputs.get("_metadata", {})

                # Aggregate data statistics
                # row_count is nested in data_metrics (from metadata extractor)
                data_metrics = metadata.get("data_metrics", {})
                row_count = data_metrics.get("row_count", 0)
                if isinstance(row_count, int):
                    total_data_rows += row_count

                # data_size is in bytes, convert to MB
                data_size_bytes = data_metrics.get("data_size", 0)
                if isinstance(data_size_bytes, (int, float)):
                    total_data_size_mb += float(data_size_bytes) / (1024 * 1024)

                # Aggregate performance statistics
                duration_ms = metadata.get("execution_duration_ms", 0)
                if isinstance(duration_ms, (int, float)):
                    total_duration_ms += int(duration_ms)

                memory_mb = metadata.get("memory_usage_mb", 0.0)
                if isinstance(memory_mb, (int, float)):
                    total_memory_mb += float(memory_mb)

        # Calculate average memory
        avg_memory_mb = total_memory_mb / total_components if total_components > 0 else 0.0

        # Get data exchange count
        exchange_statement = select(DataExchangeTable).where(
            DataExchangeTable.timestamp >= task.created_at,
            DataExchangeTable.timestamp <= latest_timestamp,
        )
        exchange_result = await self.session.exec(exchange_statement)
        total_exchanges = len(exchange_result.all())

        # Determine task status
        # Logic: if any component has error → task error
        #        if any component is running → task running
        #        otherwise → task success
        if error_components > 0:
            task_status = "error"
        elif has_running:
            task_status = "running"
        else:
            task_status = "success"

        # Update task
        task.status = task_status
        task.total_components = total_components
        task.success_components = success_components
        task.error_components = error_components
        task.total_data_rows = total_data_rows
        task.total_data_size_mb = total_data_size_mb
        task.total_exchanges = total_exchanges
        task.total_duration_ms = total_duration_ms if total_duration_ms > 0 else None
        task.avg_memory_mb = avg_memory_mb
        task.first_error_component_id = first_error_component_id
        task.first_error_message = first_error_message

        # Update timestamps
        if not task.started_at:
            task.started_at = task.created_at

        if task_status in ["success", "error"]:
            task.completed_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(task)

        logger.debug(
            f"Updated task {task.id}: status={task_status}, components={total_components}, errors={error_components}"
        )

        return task

    async def get_tasks_by_flow(
        self,
        flow_id: UUID,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TaskTable], int]:
        """Get tasks for a flow with optional filtering.

        Args:
            flow_id: UUID of the flow
            status: Optional status filter ("running" | "success" | "error")
            start_date: Optional start date filter (ISO format: YYYY-MM-DD)
            end_date: Optional end date filter (ISO format: YYYY-MM-DD)
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            tuple[list[TaskTable], int]: (tasks, total_count)
        """
        from datetime import datetime, timezone

        # Build query
        statement = select(TaskTable).where(TaskTable.flow_id == flow_id)

        if status:
            statement = statement.where(TaskTable.status == status)

        # Date range filtering
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date).replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                )
                statement = statement.where(TaskTable.created_at >= start_dt)
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date).replace(
                    hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
                )
                statement = statement.where(TaskTable.created_at <= end_dt)
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")

        # Get total count
        count_statement = select(TaskTable).where(TaskTable.flow_id == flow_id)
        if status:
            count_statement = count_statement.where(TaskTable.status == status)

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date).replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
                )
                count_statement = count_statement.where(TaskTable.created_at >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date).replace(
                    hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
                )
                count_statement = count_statement.where(TaskTable.created_at <= end_dt)
            except ValueError:
                pass

        count_result = await self.session.exec(count_statement)
        total_count = len(count_result.all())

        # Apply pagination and ordering
        statement = statement.order_by(TaskTable.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.exec(statement)
        tasks = result.all()

        return tasks, total_count

    async def get_task_detail(self, task_id: UUID) -> dict | None:
        """Get detailed information about a task including all transactions.

        Args:
            task_id: The task UUID

        Returns:
            dict | None: Task detail with transactions and exchanges, or None if not found
        """
        task = await self.get_task_by_id(task_id)
        if not task:
            return None

        # Use run_id to get exact transactions for this task
        tx_statement = (
            select(TransactionTable)
            .where(TransactionTable.run_id == task.run_id)
            .order_by(TransactionTable.timestamp.asc())
        )

        tx_result = await self.session.exec(tx_statement)
        transactions = tx_result.all()

        # Get data exchanges (keep using time window for exchanges)
        from datetime import timedelta

        time_window_end = task.completed_at if task.completed_at else (task.created_at + timedelta(hours=1))
        exchange_statement = select(DataExchangeTable).where(
            DataExchangeTable.timestamp >= task.created_at,
            DataExchangeTable.timestamp <= time_window_end,
        )

        exchange_result = await self.session.exec(exchange_statement)
        data_exchanges = exchange_result.all()

        return {
            "task": task,
            "transactions": transactions,
            "data_exchanges": data_exchanges,
        }

    async def delete_task(self, task_id: UUID) -> bool:
        """Delete a task.

        Args:
            task_id: The task UUID

        Returns:
            bool: True if deleted, False if not found
        """
        task = await self.get_task_by_id(task_id)
        if not task:
            return False

        await self.session.delete(task)
        await self.session.commit()

        logger.debug(f"Deleted task {task_id}")
        return True
