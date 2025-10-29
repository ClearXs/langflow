"""通用组件执行日志记录器

该模块提供统一的日志记录功能，适用于所有类型的Langflow组件：
- ETL组件 (table_input, kafka_input, data_cleaning等)
- LLM组件 (OpenAI, Anthropic等)
- Agent组件
- Tool组件
- Vector Store组件
- 自定义组件

通过在Vertex._build()层拦截，自动记录每个组件的执行详情。
日志存储在TransactionTable的inputs/outputs JSON字段中。

改进点：
1. 使用asyncio.create_task()实现真正的非阻塞日志记录
2. 避免await数据库操作阻塞主流程
3. 使用信号量限制并发数据库连接数
"""

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

import psutil
from lfx.log.logger import logger

if TYPE_CHECKING:
    from langflow.graph.vertex.base import Vertex

# 全局信号量，限制并发数据库连接数（避免连接池耗尽）
_db_semaphore = asyncio.Semaphore(10)

class ComponentExecutionLogger:
    """通用组件执行日志记录器

    功能：
    1. 在组件执行前记录开始状态
    2. 在组件执行后记录结果和性能指标
    3. 根据组件类型自动选择对应的MetadataExtractor
    4. 真正异步写入数据库，不阻塞主流程（使用create_task）
    """

    def __init__(self, vertex: "Vertex"):
        """初始化日志记录器

        Args:
            vertex: 要记录日志的顶点对象
        """
        self.vertex = vertex
        self.transaction_id: UUID | None = None
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
        """执行前钩子：记录开始状态（完全非阻塞）

        在组件执行前调用，记录：
        - 组件基本信息（名称、类型、类名）
        - 执行开始时间
        - 初始内存使用

        完全非阻塞策略：
        - 使用预生成的UUID作为transaction_id
        - 所有数据库操作都在后台执行
        - 立即返回，不等待任何数据库操作
        """
        # 如果 flow_id 无效，跳过日志记录
        if self.flow_id is None:
            logger.debug(f"Skipping pre-execution logging for {self.vertex.id} - no valid flow_id")
            return

        try:
            self.start_time = datetime.now(timezone.utc)
            self.start_memory_mb = self._get_memory_usage_mb()

            # 🔵 关键改进：预生成transaction_id，不依赖数据库
            from uuid import uuid4
            self.transaction_id = uuid4()

            # 提取组件参数（同步操作，不耗时）
            component_params = self._extract_component_params()

            # 构建基础inputs JSON（不包含耗时的metadata）
            inputs_json = {
                **component_params,  # 原始组件参数
                "_metadata": {
                    "component_name": self.vertex.display_name,
                    "component_type": self._determine_component_type(),
                    "component_class": self.vertex.vertex_type,
                    "execution_start_time": self.start_time.isoformat(),
                    "flow_id": str(self.flow_id),
                }
            }

            # 创建transaction记录（使用预生成的ID）
            from langflow.services.database.models.transactions.model import TransactionTable
            transaction = TransactionTable(
                id=self.transaction_id,  # 使用预生成的ID
                flow_id=self.flow_id,
                vertex_id=self.vertex.id,
                target_id=None,
                inputs=inputs_json,
                outputs=None,  # 执行后填充
                status="running",
            )

            # 🔵 完全非阻塞：所有操作都在后台执行
            task = asyncio.create_task(
                self._save_and_enrich_transaction_background(transaction, component_params)
            )
            task.add_done_callback(self._task_error_handler)

            logger.debug(f"Created transaction {self.transaction_id} for {self.vertex.display_name} (non-blocking)")

        except Exception as e:
            # 日志记录失败不应阻断组件执行
            logger.warning(f"Failed to log pre-execution for {self.vertex.display_name}: {e}")

    async def log_post_execution(
        self,
        status: str,
        results: dict | None = None,
        artifacts: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        """执行后钩子：记录结果和性能指标（完全非阻塞）

        在组件执行后调用，记录：
        - 执行结束时间和时长
        - 内存使用变化
        - 输出数据元信息（根据组件类型）
        - 错误信息（如果失败）

        完全非阻塞策略：
        - 所有数据库操作都在后台执行
        - 立即返回，不等待任何数据库操作

        Args:
            status: 执行状态 ("success" | "error")
            results: 组件执行结果
            artifacts: 组件产生的artifacts
            error: 错误对象（如果失败）
        """
        # 如果 flow_id 无效，跳过日志记录
        if self.flow_id is None:
            logger.debug(f"Skipping post-execution logging for {self.vertex.id} - no valid flow_id")
            return

        try:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - self.start_time).total_seconds() * 1000 if self.start_time else 0

            end_memory_mb = self._get_memory_usage_mb()
            memory_delta_mb = end_memory_mb - self.start_memory_mb if self.start_memory_mb else 0

            # 提取组件结果（同步操作，不耗时）
            component_results = self._extract_component_results(results, artifacts)

            # 构建基础outputs JSON（不包含耗时的output_metadata）
            outputs_json = {
                **component_results,  # 原始组件输出
                "_metadata": {
                    "execution_end_time": end_time.isoformat(),
                    "execution_duration_ms": duration_ms,
                    "memory_usage_mb": memory_delta_mb,
                    "status_detail": status,
                }
            }

            update_data = {
                "status": status,
                "outputs": outputs_json,
                "error": str(error) if error else None,
            }

            # 🔵 完全非阻塞：所有操作都在后台执行（包括状态更新）
            task = asyncio.create_task(
                self._update_and_enrich_transaction_background(
                    self.transaction_id, update_data, results, artifacts
                )
            )
            task.add_done_callback(self._task_error_handler)

            logger.debug(f"Updating transaction {self.transaction_id} for {self.vertex.display_name} (non-blocking)")

        except Exception as e:
            # 日志记录失败不应阻断组件执行
            logger.warning(f"Failed to log post-execution for {self.vertex.display_name}: {e}")

    @staticmethod
    def _task_error_handler(task: asyncio.Task) -> None:
        """后台任务错误处理器"""
        try:
            task.result()  # 获取异常（如果有）
        except Exception as e:
            logger.error(f"Background logging task failed: {e}")

    async def _save_transaction_immediately(self, transaction: Any) -> UUID | None:
        """立即保存transaction到数据库（快速，< 10ms）

        这个方法会立即执行并等待完成，确保transaction_id被设置。

        Args:
            transaction: TransactionTable对象

        Returns:
            transaction的ID
        """
        async with _db_semaphore:
            try:
                from langflow.services.deps import get_db_service

                db_service = get_db_service()
                async with db_service.with_session() as session:
                    # Ensure inputs are JSON serializable
                    if hasattr(transaction, "inputs") and isinstance(transaction.inputs, dict):
                        transaction.inputs = self._make_json_serializable(transaction.inputs)

                    session.add(transaction)
                    await session.commit()
                    await session.refresh(transaction)

                    # 保存transaction_id供后续update使用
                    self.transaction_id = transaction.id
                    logger.debug(f"Immediately saved transaction {transaction.id} for {self.vertex.display_name}")
                    return transaction.id
            except Exception as e:
                logger.error(f"Failed to immediately save transaction: {e}")
                return None

    async def _enrich_input_metadata_background(self, transaction_id: UUID, component_params: dict) -> None:
        """后台丰富输入metadata（慢速，不阻塞主流程）

        在后台提取详细的输入元信息并更新到数据库。

        Args:
            transaction_id: transaction的ID
            component_params: 组件参数字典
        """
        if not transaction_id:
            return

        async with _db_semaphore:
            try:
                # 🔵 提取输入元信息（可能耗时）
                input_metadata = {}
                try:
                    input_metadata = await self.metadata_extractor.extract_input_metadata()
                except Exception as e:
                    logger.warning(f"Failed to extract input metadata in background: {e}")

                # 🔵 如果有metadata，更新到数据库
                if input_metadata:
                    from sqlmodel import select

                    from langflow.services.database.models.transactions.model import TransactionTable
                    from langflow.services.deps import get_db_service

                    db_service = get_db_service()
                    async with db_service.with_session() as session:
                        stmt = select(TransactionTable).where(TransactionTable.id == transaction_id)
                        result = await session.exec(stmt)
                        transaction = result.first()

                        if transaction and transaction.inputs and "_metadata" in transaction.inputs:
                            # 更新metadata字段
                            transaction.inputs["_metadata"].update(input_metadata)
                            transaction.inputs = self._make_json_serializable(transaction.inputs)
                            await session.commit()
                            logger.debug(f"Background task enriched input metadata for transaction {transaction_id}")
            except Exception as e:
                logger.error(f"Failed to enrich input metadata {transaction_id}: {e}")

    async def _save_and_enrich_transaction_background(self, transaction: Any, component_params: dict) -> UUID | None:
        """后台异步保存并丰富transaction到数据库（使用信号量限制并发）

        在后台完成所有耗时的操作：
        1. 提取输入元信息
        2. 更新inputs JSON
        3. 保存到数据库

        Args:
            transaction: TransactionTable对象
            component_params: 组件参数字典

        Returns:
            transaction的ID
        """
        async with _db_semaphore:  # 限制并发数据库连接数
            try:
                # 🔵 后台操作1：提取输入元信息（可能耗时）
                input_metadata = {}
                try:
                    input_metadata = await self.metadata_extractor.extract_input_metadata()
                except Exception as e:
                    logger.warning(f"Failed to extract input metadata in background: {e}")

                # 🔵 后台操作2：丰富inputs JSON
                enriched_inputs = {
                    **component_params,
                    "_metadata": {
                        **transaction.inputs["_metadata"],
                        **input_metadata,  # 添加提取的输入元信息
                    }
                }
                transaction.inputs = enriched_inputs

                # 🔵 后台操作3：保存到数据库
                from langflow.services.deps import get_db_service

                db_service = get_db_service()
                async with db_service.with_session() as session:
                    # Ensure inputs are JSON serializable
                    if hasattr(transaction, "inputs") and isinstance(transaction.inputs, dict):
                        transaction.inputs = self._make_json_serializable(transaction.inputs)

                    session.add(transaction)
                    await session.commit()
                    await session.refresh(transaction)

                    # 保存transaction_id供后续update使用
                    self.transaction_id = transaction.id
                    logger.debug(f"Background task saved transaction {transaction.id} for {self.vertex.display_name}")
                    return transaction.id
            except Exception as e:
                logger.error(f"Failed to save and enrich transaction: {e}")
                return None

    async def _save_transaction_background(self, transaction: Any) -> UUID | None:
        """后台异步保存transaction到数据库（使用信号量限制并发）

        保留此方法用于向后兼容

        Args:
            transaction: TransactionTable对象

        Returns:
            transaction的ID
        """
        async with _db_semaphore:  # 限制并发数据库连接数
            try:
                from langflow.services.deps import get_db_service

                db_service = get_db_service()
                async with db_service.with_session() as session:
                    # Ensure inputs are JSON serializable
                    if hasattr(transaction, "inputs") and isinstance(transaction.inputs, dict):
                        transaction.inputs = self._make_json_serializable(transaction.inputs)

                    session.add(transaction)
                    await session.commit()
                    await session.refresh(transaction)

                    # 保存transaction_id供后续update使用
                    self.transaction_id = transaction.id
                    return transaction.id
            except Exception as e:
                logger.error(f"Failed to save transaction: {e}")
                return None

    async def _update_transaction_status_immediately(self, transaction_id: UUID, update_data: dict) -> None:
        """立即更新transaction状态（快速，不涉及metadata提取）

        这个方法会立即执行，确保前端能看到状态变化。

        Args:
            transaction_id: transaction的ID
            update_data: 基础更新数据（status, outputs, error）
        """
        if not transaction_id:
            return

        async with _db_semaphore:
            try:
                from sqlmodel import select

                from langflow.services.database.models.transactions.model import TransactionTable
                from langflow.services.deps import get_db_service

                db_service = get_db_service()
                async with db_service.with_session() as session:
                    stmt = select(TransactionTable).where(TransactionTable.id == transaction_id)
                    result = await session.exec(stmt)
                    transaction = result.first()

                    if transaction:
                        for key, value in update_data.items():
                            if key in ["outputs", "inputs"] and isinstance(value, dict):
                                try:
                                    value = self._make_json_serializable(value)
                                except Exception as serialization_error:
                                    logger.warning(f"Failed to serialize {key}: {serialization_error}")
                                    value = {"error": "Serialization failed", "original_type": str(type(value))}
                            setattr(transaction, key, value)
                        await session.commit()
                        logger.debug(f"Immediately updated transaction {transaction_id} status for {self.vertex.display_name}")
            except Exception as e:
                logger.error(f"Failed to immediately update transaction {transaction_id}: {e}")

    async def _enrich_transaction_metadata_background(
        self, transaction_id: UUID, results: dict | None, artifacts: dict | None
    ) -> None:
        """后台丰富transaction的metadata（慢速，不阻塞主流程）

        在后台提取详细的输出元信息并更新到数据库。

        Args:
            transaction_id: transaction的ID
            results: 组件执行结果
            artifacts: 组件产生的artifacts
        """
        if not transaction_id:
            return

        async with _db_semaphore:
            try:
                # 🔵 提取输出元信息（可能很耗时）
                output_metadata = {}
                try:
                    output_metadata = await self.metadata_extractor.extract_output_metadata(
                        results=results,
                        artifacts=artifacts,
                    )
                except Exception as e:
                    logger.warning(f"Failed to extract output metadata in background: {e}")

                # 🔵 如果有metadata，更新到数据库
                if output_metadata:
                    from sqlmodel import select

                    from langflow.services.database.models.transactions.model import TransactionTable
                    from langflow.services.deps import get_db_service

                    db_service = get_db_service()
                    async with db_service.with_session() as session:
                        stmt = select(TransactionTable).where(TransactionTable.id == transaction_id)
                        result = await session.exec(stmt)
                        transaction = result.first()

                        if transaction and transaction.outputs and "_metadata" in transaction.outputs:
                            # 更新metadata字段
                            transaction.outputs["_metadata"].update(output_metadata)
                            transaction.outputs = self._make_json_serializable(transaction.outputs)
                            await session.commit()
                            logger.debug(f"Background task enriched metadata for transaction {transaction_id}")
            except Exception as e:
                logger.error(f"Failed to enrich transaction metadata {transaction_id}: {e}")

    async def _update_and_enrich_transaction_background(
        self, transaction_id: UUID, update_data: dict, results: dict | None, artifacts: dict | None
    ) -> None:
        """后台异步更新并丰富transaction记录（使用信号量限制并发）

        在后台完成所有耗时的操作：
        1. 提取输出元信息（可能涉及数据分析和采样）
        2. 丰富outputs JSON
        3. 更新数据库

        Args:
            transaction_id: transaction的ID
            update_data: 基础更新数据
            results: 组件执行结果
            artifacts: 组件产生的artifacts
        """
        if not transaction_id:
            return

        async with _db_semaphore:  # 限制并发数据库连接数
            try:
                # 🔵 后台操作1：提取输出元信息（可能很耗时）
                output_metadata = {}
                try:
                    output_metadata = await self.metadata_extractor.extract_output_metadata(
                        results=results,
                        artifacts=artifacts,
                    )
                except Exception as e:
                    logger.warning(f"Failed to extract output metadata in background: {e}")

                # 🔵 后台操作2：丰富outputs JSON
                if "outputs" in update_data and "_metadata" in update_data["outputs"]:
                    update_data["outputs"]["_metadata"].update(output_metadata)

                # 🔵 后台操作3：更新数据库
                from sqlmodel import select

                from langflow.services.database.models.transactions.model import TransactionTable
                from langflow.services.deps import get_db_service

                db_service = get_db_service()
                async with db_service.with_session() as session:
                    stmt = select(TransactionTable).where(TransactionTable.id == transaction_id)
                    result = await session.exec(stmt)
                    transaction = result.first()

                    if transaction:
                        for key, value in update_data.items():
                            # Handle JSON serialization for complex objects
                            if key in ["outputs", "inputs"] and isinstance(value, dict):
                                try:
                                    # Recursively convert non-serializable objects
                                    value = self._make_json_serializable(value)
                                except Exception as serialization_error:
                                    logger.warning(f"Failed to serialize {key} for transaction {transaction_id}: {serialization_error}")
                                    # Set a safe fallback value
                                    value = {"error": "Serialization failed", "original_type": str(type(value))}
                            setattr(transaction, key, value)
                        await session.commit()
                        logger.debug(f"Background task updated transaction {transaction_id} for {self.vertex.display_name}")
            except Exception as e:
                logger.error(f"Failed to update and enrich transaction {transaction_id}: {e}")

    async def _update_transaction_background(self, transaction_id: UUID, update_data: dict) -> None:
        """后台异步更新transaction记录（使用信号量限制并发）

        Args:
            transaction_id: transaction的ID
            update_data: 要更新的数据
        """
        if not transaction_id:
            return

        async with _db_semaphore:  # 限制并发数据库连接数
            try:
                from sqlmodel import select

                from langflow.services.database.models.transactions.model import TransactionTable
                from langflow.services.deps import get_db_service

                db_service = get_db_service()
                async with db_service.with_session() as session:
                    stmt = select(TransactionTable).where(TransactionTable.id == transaction_id)
                    result = await session.exec(stmt)
                    transaction = result.first()

                    if transaction:
                        for key, value in update_data.items():
                            # Handle JSON serialization for complex objects
                            if key in ["outputs", "inputs"] and isinstance(value, dict):
                                try:
                                    # Recursively convert non-serializable objects
                                    value = self._make_json_serializable(value)
                                except Exception as serialization_error:
                                    logger.warning(f"Failed to serialize {key} for transaction {transaction_id}: {serialization_error}")
                                    # Set a safe fallback value
                                    value = {"error": "Serialization failed", "original_type": str(type(value))}
                            setattr(transaction, key, value)
                        await session.commit()
            except Exception as e:
                logger.error(f"Failed to update transaction {transaction_id}: {e}")

    def _determine_component_type(self) -> str:
        """根据组件类名判断组件类型

        Returns:
            组件类型字符串，可能的值：
            - etl_input: ETL输入组件
            - etl_transformation: ETL转换组件
            - etl_operation: ETL操作组件
            - etl_output: ETL输出组件
            - model: LLM模型组件
            - agent: Agent组件
            - tool: 工具组件
            - vector: 向量存储组件
            - data: 数据处理组件
            - prompt: Prompt组件
            - other: 其他组件
        """
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
        if "model" in component_class or "llm" in component_class or "openai" in component_class or "anthropic" in component_class:
            return "model"
        if "agent" in component_class:
            return "agent"
        if "tool" in component_class:
            return "tool"
        if "vector" in component_class or "store" in component_class:
            return "vector"
        if "prompt" in component_class:
            return "prompt"
        if "data" in component_class:
            return "data"
        return "other"

    def _extract_component_params(self) -> dict:
        """提取组件的参数值

        Returns:
            组件参数字典
        """
        if not self.vertex.params:
            return {}

        params = {}
        for param_name, param_value in self.vertex.params.items():
            try:
                # 尝试获取参数值
                if hasattr(param_value, "value"):
                    params[param_name] = param_value.value
                else:
                    params[param_name] = param_value
            except Exception:
                params[param_name] = str(param_value)

        return params

    def _extract_component_results(self, results: dict | None, artifacts: dict | None) -> dict:
        """提取组件的输出结果

        Args:
            results: 组件results字典
            artifacts: 组件artifacts字典

        Returns:
            组件输出字典
        """
        output = {}

        if results:
            output["results"] = results

        if artifacts:
            output["artifacts"] = artifacts

        return output

    def _get_memory_usage_mb(self) -> float:
        """获取当前进程的内存使用量（MB）

        Returns:
            内存使用量（MB）
        """
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def _make_json_serializable(self, obj: any) -> any:
        """递归将对象转换为JSON可序列化的格式

        Args:
            obj: 需要序列化的对象

        Returns:
            JSON可序列化的对象
        """
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        if isinstance(obj, dict):
            return {
                str(key): self._make_json_serializable(value)
                for key, value in obj.items()
            }
        if hasattr(obj, "__dict__"):
            # 尝试序列化有__dict__的对象
            try:
                return {
                    "_type": type(obj).__name__,
                    "_module": type(obj).__module__,
                    "_data": self._make_json_serializable(obj.__dict__)
                }
            except Exception:
                return {
                    "_type": type(obj).__name__,
                    "_module": type(obj).__module__,
                    "_repr": str(obj)
                }
        else:
            # 对于其他类型，尝试转换为字符串
            try:
                # 尝试JSON序列化来测试
                import json
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
