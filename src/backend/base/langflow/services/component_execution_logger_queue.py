"""基于队列的组件执行日志记录器

使用生产者-消费者模式，避免阻塞主执行流程：
1. 主线程快速将日志任务放入队列
2. 单独的消费者协程处理队列中的任务
3. 保证日志按顺序处理，避免数据库连接争抢
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import psutil
from lfx.log.logger import logger

if TYPE_CHECKING:
    from langflow.graph.vertex.base import Vertex

# 全局日志队列
_log_queue: asyncio.Queue | None = None
_consumer_task: asyncio.Task | None = None


class LogTask:
    """日志任务"""

    def __init__(self, task_type: str, data: dict):
        self.task_type = task_type  # 'create' | 'update'
        self.data = data


async def _get_log_queue() -> asyncio.Queue:
    """获取或创建全局日志队列"""
    global _log_queue, _consumer_task

    if _log_queue is None:
        _log_queue = asyncio.Queue(maxsize=1000)  # 最多1000个待处理任务
        # 启动消费者
        _consumer_task = asyncio.create_task(_log_consumer())
        logger.info("Started execution log consumer")

    return _log_queue


async def _log_consumer():
    """日志消费者：从队列中取出任务并处理"""
    from sqlmodel import select

    from langflow.services.database.models.transactions.model import TransactionTable
    from langflow.services.deps import get_db_service

    logger.info("Log consumer started")

    while True:
        try:
            # 从队列获取任务（阻塞等待）
            task: LogTask = await _log_queue.get()

            try:
                db_service = get_db_service()

                if task.task_type == "create":
                    # 创建新的transaction记录
                    async with db_service.with_session() as session:
                        transaction = TransactionTable(**task.data)
                        session.add(transaction)
                        await session.commit()
                        logger.debug(
                            f"[QueueConsumer] Created transaction {transaction.id} with run_id={transaction.run_id}"
                        )

                elif task.task_type == "update":
                    # 更新existing transaction
                    transaction_id = task.data.pop("id")
                    async with db_service.with_session() as session:
                        stmt = select(TransactionTable).where(TransactionTable.id == transaction_id)
                        result = await session.exec(stmt)
                        transaction = result.first()

                        if transaction:
                            for key, value in task.data.items():
                                setattr(transaction, key, value)
                            await session.commit()
                            logger.debug(
                                f"[QueueConsumer] Updated transaction {transaction_id} to status={transaction.status}"
                            )
                        else:
                            logger.warning(f"Transaction {transaction_id} not found")

            except Exception as e:
                logger.error(
                    f"Failed to process log task: {e}",
                    extra={
                        "task_type": task.task_type,
                        "vertex_id": task.data.get("vertex_id"),
                        "flow_id": task.data.get("flow_id"),
                        "flow_id_type": type(task.data.get("flow_id")).__name__,
                        "transaction_id": task.data.get("id"),
                    },
                )
            finally:
                _log_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Log consumer cancelled")
            break
        except Exception as e:
            logger.error(f"Log consumer error: {e}")
            await asyncio.sleep(1)  # 避免疯狂循环


class ComponentExecutionLogger:
    """基于队列的组件执行日志记录器"""

    def __init__(self, vertex: "Vertex"):
        """初始化日志记录器

        Args:
            vertex: 要记录日志的顶点对象
        """
        self.vertex = vertex
        self.transaction_id: UUID = uuid4()  # 预生成UUID
        self.start_time: datetime | None = None
        self.start_memory_mb: float | None = None

        # 验证并标准化 flow_id
        if self.vertex.graph and self.vertex.graph.flow_id:
            try:
                if isinstance(self.vertex.graph.flow_id, str):
                    self.flow_id = UUID(self.vertex.graph.flow_id)
                elif isinstance(self.vertex.graph.flow_id, UUID):
                    self.flow_id = self.vertex.graph.flow_id
                else:
                    logger.warning(
                        f"Invalid flow_id type for vertex {vertex.id}: {type(self.vertex.graph.flow_id).__name__}"
                    )
                    self.flow_id = None
            except ValueError as e:
                logger.warning(f"Invalid flow_id format for vertex {vertex.id}: {e}")
                self.flow_id = None
        else:
            self.flow_id = None

        # 导入MetadataExtractor（延迟导入避免循环依赖）
        from langflow.services.metadata_extractors import get_metadata_extractor

        self.metadata_extractor = get_metadata_extractor(vertex)

    async def log_pre_execution(self) -> None:
        """执行前钩子：快速记录开始状态（非阻塞）"""
        # 如果 flow_id 无效，跳过日志记录
        if self.flow_id is None:
            logger.debug(f"Skipping pre-execution logging for {self.vertex.id} - no valid flow_id")
            return

        try:
            self.start_time = datetime.now(timezone.utc)
            self.start_memory_mb = self._get_memory_usage_mb()

            # 提取组件参数（同步操作）
            component_params = self._extract_component_params()

            # 构建inputs JSON
            inputs_json = {
                **component_params,
                "_metadata": {
                    "component_name": self.vertex.display_name,
                    "component_type": self._determine_component_type(),
                    "component_class": self.vertex.vertex_type,
                    "execution_start_time": self.start_time.isoformat(),
                    "flow_id": str(self.flow_id),
                },
            }

            # 序列化数据
            inputs_json = self._make_json_serializable(inputs_json)

            # Get run_id from graph if available
            run_id = None
            if self.vertex.graph:
                try:
                    # Access _run_id directly to avoid ValueError if not set
                    run_id = getattr(self.vertex.graph, "_run_id", None)
                    if run_id:
                        logger.debug(f"[QueueLogger] Got run_id from graph._run_id: {run_id}")
                except Exception as e:
                    logger.warning(f"[QueueLogger] Failed to get _run_id: {e}")
                    # Fallback: try the property (may raise ValueError)
                    try:
                        run_id = self.vertex.graph.run_id
                        logger.debug(f"[QueueLogger] Got run_id from graph.run_id property: {run_id}")
                    except (ValueError, AttributeError) as e2:
                        logger.warning(f"[QueueLogger] Failed to get run_id property: {e2}")

            if not run_id:
                logger.warning(f"[QueueLogger] run_id is None for vertex {self.vertex.id}, graph: {self.vertex.graph}")

            # 创建日志任务并放入队列（非阻塞）
            queue = await _get_log_queue()
            task = LogTask(
                "create",
                {
                    "id": self.transaction_id,
                    "flow_id": self.flow_id,
                    "run_id": run_id,  # 添加 run_id
                    "vertex_id": self.vertex.id,
                    "target_id": None,
                    "inputs": inputs_json,
                    "outputs": None,
                    "status": "running",
                },
            )

            logger.debug(f"[QueueLogger] Queued transaction {self.transaction_id} with run_id={run_id}")

            queue.put_nowait(task)  # 非阻塞放入队列

        except Exception as e:
            logger.warning(f"Failed to queue pre-execution log: {e}")

    async def log_post_execution(
        self,
        status: str,
        results: dict | None = None,
        artifacts: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        """执行后钩子：快速记录结果（非阻塞）"""
        # 如果 flow_id 无效，跳过日志记录
        if self.flow_id is None:
            logger.debug(f"Skipping post-execution logging for {self.vertex.id} - no valid flow_id")
            return

        try:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - self.start_time).total_seconds() * 1000 if self.start_time else 0

            end_memory_mb = self._get_memory_usage_mb()
            memory_delta_mb = end_memory_mb - self.start_memory_mb if self.start_memory_mb else 0

            # 提取组件结果（同步操作）
            component_results = self._extract_component_results(results, artifacts)

            # 🔴 提取输出元信息（关键步骤）
            output_metadata = {}
            try:
                logger.info(
                    f"[METADATA_DEBUG] Starting metadata extraction in queue for component: {self.vertex.vertex_type}"
                )
                logger.info(f"[METADATA_DEBUG] Results available in queue: {results is not None}")
                logger.info(f"[METADATA_DEBUG] Results keys in queue: {list(results.keys()) if results else 'None'}")

                output_metadata = await self.metadata_extractor.extract_output_metadata(
                    results=results,
                    artifacts=artifacts,
                )

                logger.info(f"[METADATA_DEBUG] Extracted output_metadata in queue: {output_metadata}")
            except Exception as e:
                logger.error(f"[METADATA_DEBUG] Failed to extract output metadata in queue: {e}")
                import traceback

                logger.error(f"[METADATA_DEBUG] Traceback: {traceback.format_exc()}")

            # 构建outputs JSON
            outputs_json = {
                **component_results,
                "_metadata": {
                    "execution_end_time": end_time.isoformat(),
                    "execution_duration_ms": duration_ms,
                    "memory_usage_mb": memory_delta_mb,
                    "status_detail": status,
                    **output_metadata,  # 🔴 合并提取的输出元信息（包含data_metrics）
                },
            }

            # 序列化数据
            outputs_json = self._make_json_serializable(outputs_json)

            # 创建更新任务并放入队列（非阻塞）
            queue = await _get_log_queue()
            task = LogTask(
                "update",
                {
                    "id": self.transaction_id,
                    "status": status,
                    "outputs": outputs_json,
                    "error": str(error) if error else None,
                },
            )

            queue.put_nowait(task)  # 非阻塞放入队列
            logger.debug(f"Queued post-execution log for {self.vertex.display_name}")

        except Exception as e:
            logger.warning(f"Failed to queue post-execution log: {e}")

    def _get_memory_usage_mb(self) -> float:
        """获取当前进程的内存使用量（MB）"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def _extract_component_params(self) -> dict:
        """提取组件参数（排除大型字段）."""
        # Fields to exclude from logging (large content fields)
        excluded_fields = {
            "code",  # Python/SQL/Shell script code
            "sql_script",  # SQL script content
            "script",  # Generic script content
            "prompt_template",  # Large prompt templates
            "system_message",  # Large system messages
        }
        max_field_size = 5000  # Maximum size for string fields

        params = {}
        if hasattr(self.vertex, "params") and self.vertex.params:
            for key, value in self.vertex.params.items():
                # Skip excluded large fields
                if key in excluded_fields:
                    # Store a placeholder indicating the field was excluded
                    params[key] = f"<excluded: {key}>"
                    continue

                # 提取参数值
                if hasattr(value, "value"):
                    extracted_value = value.value
                    # Additional check: exclude if value is a very large string
                    if isinstance(extracted_value, str) and len(extracted_value) > max_field_size:
                        params[key] = f"<large content excluded: {len(extracted_value)} chars>"
                    else:
                        params[key] = extracted_value
                else:
                    params[key] = value
        return params

    def _extract_component_results(self, results: dict | None, artifacts: dict | None) -> dict:
        """提取组件执行结果"""
        component_results = {}

        if results:
            component_results["results"] = results

        if artifacts:
            component_results["artifacts"] = artifacts

        return component_results

    def _determine_component_type(self) -> str:
        """判断组件类型"""
        component_class = self.vertex.vertex_type.lower()

        # ETL组件判断
        if "input" in component_class and "etl" in component_class:
            return "etl_input"
        if "output" in component_class and "etl" in component_class:
            return "etl_output"
        if any(x in component_class for x in ["cleaning", "mapping", "pivot", "split", "merge"]):
            return "etl_transformation"
        if any(x in component_class for x in ["join", "union", "group", "dedup"]):
            return "etl_operation"

        # Langflow原生组件判断
        if "model" in component_class or "llm" in component_class:
            return "model"
        if "agent" in component_class:
            return "agent"
        if "tool" in component_class:
            return "tool"
        if "vector" in component_class or "store" in component_class:
            return "vector"
        if "prompt" in component_class:
            return "prompt"

        return "other"

    def _make_json_serializable(self, obj: Any) -> Any:
        """递归转换对象为JSON可序列化格式."""
        if obj is None:
            return None

        if isinstance(obj, (str, int, float, bool)):
            # Check if string is too large
            if isinstance(obj, str) and len(obj) > 5000:
                return f"<large string: {len(obj)} chars>"
            return obj

        if isinstance(obj, (datetime,)):
            return obj.isoformat()

        if isinstance(obj, UUID):
            return str(obj)

        # Special handling for Vertex objects to exclude large fields
        if hasattr(obj, "__class__") and obj.__class__.__name__ == "Vertex":
            return self._serialize_vertex(obj)

        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}

        if isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]

        # 其他对象转为字符串（但限制长度）
        try:
            obj_str = str(obj)
            if len(obj_str) > 1000:  # Limit object string representation
                return f"<{type(obj).__name__}: {len(obj_str)} chars>"
            return obj_str
        except Exception:  # noqa: BLE001
            return f"<{type(obj).__name__}>"

    def _serialize_vertex(self, vertex) -> dict:
        """序列化 Vertex 对象，排除大型字段."""
        try:
            return {
                "vertex_type": "Vertex",
                "display_name": getattr(vertex, "display_name", "Unknown"),
                "id": getattr(vertex, "id", "Unknown"),
                "vertex_class": getattr(vertex, "vertex_type", "Unknown"),
                # Exclude: data, params (which contain code), and other large fields
                "_note": "Large fields excluded (code, params, data)",
            }
        except Exception:  # noqa: BLE001
            return {
                "vertex_type": "Vertex",
                "_note": "Failed to serialize vertex details",
            }
