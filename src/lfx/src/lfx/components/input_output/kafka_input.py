import json
import time
from collections.abc import AsyncGenerator, Generator
from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    TableInput,
)
from lfx.log.logger import logger
from lfx.schema import Data
from lfx.streaming import streaming_component

# Constants
SAMPLE_CACHE_SIZE = 5


@streaming_component
class ETLKafkaInputComponent(Component):
    display_name = i18n.t("components.input_output.kafka_input.display_name")
    description = i18n.t("components.input_output.kafka_input.description")
    icon = "activity"
    name = "ETLKafkaInput"
    is_streaming_component = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sample_data_cache = []  # 缓存样本数据
        self._current_consumer = None  # Track current consumer instance
        self._should_stop = False  # 停止标志

    def _is_design_time_context(self) -> bool:
        """检测是否在设计时上下文中（字段分析等）"""

        # 方法1: 检查调用栈 - 最可靠的检测方法
        import traceback
        stack = traceback.extract_stack()

        for i, frame in enumerate(stack):
            # 检测字段分析相关的调用
            if "analyze_fields" in frame.name or "field_analysis" in frame.name:
                logger.debug("[KafkaInput] Field analysis detected in call stack, returning sample data")
                return True
            # 检测GraphUtils的临时图执行 - 修复：使用OR而不是AND
            if "GraphUtils" in frame.filename or "execute_node_and_get_result" in frame.name:
                logger.debug("[KafkaInput] GraphUtils execution detected, assuming design-time context")
                return True
            # 检测字段分析相关的上下文
            if "FieldNameMapping" in frame.filename or "field_name_mapping" in frame.filename:
                logger.debug("[KafkaInput] Field name mapping context detected, assuming design-time")
                return True

        # 方法2: 检查是否有schema定义但没有活跃的Kafka连接配置
        # 如果用户定义了schema，很可能是设计时配置
        if self.message_schema:
            # 检查是否使用了默认/示例配置
            if (not self.bootstrap_servers or
                self.bootstrap_servers.strip() == "" or
                self.bootstrap_servers in ["localhost:9092", "localhost:9093"] or
                self.bootstrap_servers.startswith("example") or
                self.topics in ["test-topic", "example-topic", "sample-topic"]):
                logger.debug("[KafkaInput] Schema with example config detected, assuming design-time")
                return True

        # 方法3: 检查字段提取模式是否为schema_only（这通常只用于设计时）
        if hasattr(self, 'field_extraction_mode') and self.field_extraction_mode == "schema_only":
            logger.debug("[KafkaInput] Schema-only mode detected, assuming design-time")
            return True

        return False

    def _has_valid_runtime_config(self) -> bool:
        """检查是否有有效的运行时配置"""
        # 简单检查：如果有真实的服务器地址和topics，认为是运行时
        has_server = (self.bootstrap_servers and
                     self.bootstrap_servers.strip() != "" and
                     self.bootstrap_servers != "localhost:9092")
        has_topics = self.topics and self.topics.strip() != ""
        return has_server and has_topics

    def __del__(self):
        """Cleanup when component is destroyed."""
        try:
            self._should_stop = True
            if self._current_consumer:
                self._current_consumer.close()
                logger.info("Component destroyed, consumer closed")
        except Exception:
            pass  # Ignore errors during cleanup

    def stop(self):
        """停止消费（可被外部调用）"""
        logger.info("Stop requested")
        self._should_stop = True
        self._close_current_consumer()

    inputs = [
        MessageTextInput(
            name="bootstrap_servers",
            display_name=i18n.t("components.input_output.kafka_input.bootstrap_servers.display_name"),
            info=i18n.t("components.input_output.kafka_input.bootstrap_servers.info"),
            required=True,
            placeholder="localhost:9092",
        ),
        MessageTextInput(
            name="topics",
            display_name=i18n.t("components.input_output.kafka_input.topics.display_name"),
            info=i18n.t("components.input_output.kafka_input.topics.info"),
            required=True,
            placeholder="topic1,topic2",
        ),
        MessageTextInput(
            name="group_id",
            display_name=i18n.t("components.input_output.kafka_input.group_id.display_name"),
            info=i18n.t("components.input_output.kafka_input.group_id.info"),
            value="langflow-etl-consumer",
            advanced=True,
        ),
        MessageTextInput(
            name="value_deserializer",
            display_name=i18n.t("components.input_output.kafka_input.value_deserializer.display_name"),
            info=i18n.t("components.input_output.kafka_input.value_deserializer.info"),
            value="json",
            advanced=True,
        ),
        DropdownInput(
            name="auto_offset_reset",
            display_name=i18n.t("components.input_output.kafka_input.auto_offset_reset.display_name"),
            info=i18n.t("components.input_output.kafka_input.auto_offset_reset.info"),
            options=["latest", "earliest", "none"],
            value="latest",
        ),
        BoolInput(
            name="reset_offsets",
            display_name=i18n.t("components.input_output.kafka_input.reset_offsets.display_name"),
            info=i18n.t("components.input_output.kafka_input.reset_offsets.info"),
            value=False,
            advanced=True,
        ),
        IntInput(
            name="max_messages",
            display_name=i18n.t("components.input_output.kafka_input.max_messages.display_name"),
            info=i18n.t("components.input_output.kafka_input.max_messages.info"),
            value=100,
            advanced=True,
        ),
        IntInput(
            name="timeout_ms",
            display_name=i18n.t("components.input_output.kafka_input.timeout_ms.display_name"),
            info=i18n.t("components.input_output.kafka_input.timeout_ms.info"),
            value=300000,  # 增加到5分钟，支持更长的消费时间
            advanced=True,
        ),
        IntInput(
            name="stream_timeout_minutes",
            display_name=i18n.t("components.input_output.kafka_input.stream_timeout_minutes.display_name"),
            info=i18n.t("components.input_output.kafka_input.stream_timeout_minutes.info"),
            value=30,  # 30分钟流式超时
            advanced=True,
        ),
        BoolInput(
            name="debug_mode",
            display_name=i18n.t("components.input_output.kafka_input.debug_mode.display_name"),
            info=i18n.t("components.input_output.kafka_input.debug_mode.info"),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="force_new_group",
            display_name=i18n.t("components.input_output.kafka_input.force_new_group.display_name"),
            info=i18n.t("components.input_output.kafka_input.force_new_group.info"),
            value=True,  # 默认强制使用新的Consumer Group
            advanced=True,
        ),
        BoolInput(
            name="keep_consumer_alive",
            display_name=i18n.t("components.input_output.kafka_input.keep_consumer_alive.display_name"),
            info=i18n.t("components.input_output.kafka_input.keep_consumer_alive.info"),
            value=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.input_output.kafka_input.batch_size.display_name"),
            info=i18n.t("components.input_output.kafka_input.batch_size.info"),
            value=10,
            advanced=True,
        ),
        DropdownInput(
            name="output_format",
            display_name=i18n.t("components.input_output.kafka_input.output_format.display_name"),
            info=i18n.t("components.input_output.kafka_input.output_format.info"),
            options=["raw", "flattened"],
            value="raw",
            advanced=True,
        ),
        DropdownInput(
            name="field_extraction_mode",
            display_name=i18n.t("components.input_output.kafka_input.field_extraction_mode.display_name"),
            info=i18n.t("components.input_output.kafka_input.field_extraction_mode.info"),
            options=["auto", "schema_only", "flatten_all"],
            value="auto",
            advanced=True,
        ),
        TableInput(
            name="message_schema",
            display_name=i18n.t("components.input_output.kafka_input.message_schema.display_name"),
            info=i18n.t("components.input_output.kafka_input.message_schema.info"),
            table_schema=[
                {
                    "name": "field_name",
                    "type": "str",
                    "display_name": i18n.t("components.input_output.kafka_input.message_schema.field_name"),
                },
                {
                    "name": "field_type",
                    "type": "str",
                    "display_name": i18n.t("components.input_output.kafka_input.message_schema.data_type"),
                    "options": ["string", "int", "float", "bool", "json", "timestamp"],
                },
                {
                    "name": "json_path",
                    "type": "str",
                    "display_name": i18n.t("components.input_output.kafka_input.message_schema.json_path"),
                    "placeholder": "$.user.name",
                },
                {
                    "name": "required",
                    "type": "bool",
                    "display_name": i18n.t("components.input_output.kafka_input.message_schema.required"),
                    "formatter": "boolean",
                },
                {
                    "name": "description",
                    "type": "str",
                    "display_name": i18n.t("components.input_output.kafka_input.message_schema.description"),
                },
            ],
            value=[],
            table_options={
                "action_buttons": [
                    {
                        "name": "auto_detect_schema",
                        "label": i18n.t("components.input_output.kafka_input.message_schema.auto_detect_schema"),
                        "icon": "RefreshCw",
                        "position": "top",
                    }
                ]
            },
        ),
        BoolInput(
            name="auto_commit",
            display_name=i18n.t("components.input_output.kafka_input.auto_commit.display_name"),
            info=i18n.t("components.input_output.kafka_input.auto_commit.info"),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="json_path",
            display_name=i18n.t("components.input_output.kafka_input.json_path.display_name"),
            info=i18n.t("components.input_output.kafka_input.json_path.info"),
            placeholder="$.data",
            advanced=True,
        ),
        MessageTextInput(
            name="sasl_username",
            display_name=i18n.t("components.input_output.kafka_input.sasl_username.display_name"),
            info=i18n.t("components.input_output.kafka_input.sasl_username.info"),
            advanced=True,
        ),
        SecretStrInput(
            name="sasl_password",
            display_name=i18n.t("components.input_output.kafka_input.sasl_password.display_name"),
            info=i18n.t("components.input_output.kafka_input.sasl_password.info"),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t("components.input_output.kafka_input.outputs.data.display_name"),
            method="consume_messages",
            types=["Data"],
        ),
        Output(
            name="sample_data",
            display_name=i18n.t("components.input_output.kafka_input.outputs.sample_data.display_name"),
            method="get_sample_data",
            types=["Data"],
        ),
        Output(
            name="consumer_info",
            display_name=i18n.t("components.input_output.kafka_input.outputs.consumer_info.display_name"),
            method="get_consumer_info",
            types=["Data"],
        ),
    ]

    def _close_current_consumer(self):
        """关闭当前 Consumer"""
        if self._current_consumer:
            logger.info("Closing consumer...")
            try:
                self._current_consumer.close()
                logger.info("Consumer closed successfully")
            except Exception as e:
                logger.error(f"Failed to close consumer: {e}")
            finally:
                self._current_consumer = None

    def _create_consumer(self):
        """创建 Consumer 并记录详细信息"""
        import time
        import uuid

        from confluent_kafka import Consumer

        # 如果启用强制新组，生成唯一的组ID
        effective_group_id = self.group_id
        if self.force_new_group:
            timestamp = int(time.time())
            unique_id = str(uuid.uuid4())[:8]
            effective_group_id = f"{self.group_id}-{timestamp}-{unique_id}"
            logger.debug(f"Using unique group_id: {effective_group_id}")

        # 配置 consumer
        consumer_config = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": effective_group_id,
            "auto.offset.reset": self.auto_offset_reset,
            "enable.auto.commit": self.auto_commit,
            "session.timeout.ms": 30000,
            "request.timeout.ms": 40000,
            "heartbeat.interval.ms": 3000,
        }

        # 添加 SASL 认证
        if self.sasl_username and self.sasl_password:
            consumer_config.update(
                {
                    "security.protocol": "SASL_PLAINTEXT",
                    "sasl.mechanism": "PLAIN",
                    "sasl.username": self.sasl_username,
                    "sasl.password": self.sasl_password,
                }
            )

        logger.debug(f"Consumer config: servers={self.bootstrap_servers}, group={effective_group_id}")

        consumer = Consumer(consumer_config)
        logger.info("Consumer created successfully")

        return consumer

    def _log_subscription_info(self, consumer, topics):
        """记录订阅信息"""
        try:
            # 获取集群元数据
            metadata = consumer.list_topics(timeout=5.0)

            logger.info("━━━ Kafka Cluster Info ━━━")
            logger.info(f"Brokers: {len(metadata.brokers)} nodes")
            broker_list = [f"{broker.host}:{broker.port}" for broker in metadata.brokers.values()]
            logger.info(f"Broker list: {', '.join(broker_list[:3])}{' ...' if len(broker_list) > 3 else ''}")
            cluster_id = getattr(metadata, "cluster_id", "N/A")
            logger.info(f"Cluster ID: {cluster_id}")

            logger.info("━━━ Subscription Info ━━━")
            logger.info(f"Topics to subscribe: {topics}")

            # 检查主题是否存在并显示详情
            for topic in topics:
                if topic in metadata.topics:
                    topic_meta = metadata.topics[topic]
                    partition_count = len(topic_meta.partitions)
                    logger.info(f"  ✓ {topic}: {partition_count} partition(s)")

                    # 显示每个分区的信息
                    for partition_id, partition in topic_meta.partitions.items():
                        if partition.error:
                            logger.info(f"    - Partition {partition_id}: ERROR - {partition.error}")
                        else:
                            logger.info(f"    - Partition {partition_id}: {len(partition.replicas)} replica(s)")
                else:
                    logger.info(f"  ✗ {topic}: NOT FOUND (will cause subscription error)")

        except Exception as e:
            logger.info(f"Failed to get subscription info: {e}")

    def _wait_for_assignment(self, consumer):
        """等待分区分配完成"""
        logger.info("Waiting for partition assignment...")
        max_wait = 10  # 最多等待10秒
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 触发分区分配
            consumer.poll(timeout=0.5)

            # 检查是否已分配
            assignment = consumer.assignment()
            if assignment:
                logger.info(f"✓ Partitions assigned after {time.time() - start_time:.1f}s")
                return True

        logger.info("⚠️  No partitions assigned after 10s (may be normal if no partitions available)")
        return False

    def _log_partition_assignment(self, consumer):
        """记录分区分配详情"""
        try:
            assignment = consumer.assignment()

            logger.info("━━━ Partition Assignment ━━━")
            if not assignment:
                logger.info("  No partitions assigned")
                return

            logger.info(f"  Assigned {len(assignment)} partition(s):")

            for tp in assignment:
                try:
                    # 获取已提交的 offset
                    committed = consumer.committed([tp], timeout=5.0)
                    current_offset = (
                        committed[0].offset if committed and committed[0] and committed[0].offset >= 0 else -1
                    )

                    # 获取 watermark offsets
                    low, high = consumer.get_watermark_offsets(tp, timeout=5.0)

                    # 计算 lag
                    if current_offset >= 0:
                        lag = high - current_offset
                    else:
                        lag = high  # 如果没有提交过，lag 就是全部消息数

                    logger.info(f"    • {tp.topic}-{tp.partition}:")
                    logger.info(f"      Current offset: {current_offset}")
                    logger.info(f"      High watermark: {high}")
                    logger.info(f"      Consumer lag: {lag}")

                except Exception as e:
                    logger.info(f"    • {tp.topic}-{tp.partition}: Failed to get info - {e}")

        except Exception as e:
            logger.info(f"Failed to get partition assignment: {e}")

    def _poll_messages(self, consumer, topics):
        """轮询消息并记录详细诊断"""
        from confluent_kafka import KafkaError

        results = []

        logger.info("━━━ Starting Message Poll ━━━")
        logger.info(f"Max messages: {self.max_messages}")
        logger.info(f"Timeout: {self.timeout_ms}ms ({self.timeout_ms / 1000:.1f}s)")
        logger.info(f"Auto offset reset: {self.auto_offset_reset}")
        logger.info(f"Force new group: {self.force_new_group}")

        # 检查分区水位线信息
        try:
            assignment = consumer.assignment()
            if assignment:
                logger.info("📊 Initial partition watermarks:")
                for tp in assignment:
                    low, high = consumer.get_watermark_offsets(tp, timeout=5.0)
                    logger.info(f"  {tp.topic}-{tp.partition}: low={low}, high={high}, available={high - low} messages")
            else:
                logger.info("⚠️  No partitions assigned yet")
        except Exception as e:
            logger.info(f"⚠️  Failed to get watermarks: {e}")

        poll_count = 0
        eof_count = 0
        start_time = time.time()
        last_log_time = start_time
        timeout_seconds = self.timeout_ms / 1000.0

        while len(results) < self.max_messages:
            # 检查超时
            if time.time() - start_time > timeout_seconds:
                logger.info(f"⏱️  Timeout reached after {timeout_seconds:.1f}s")
                break

            poll_count += 1
            msg = consumer.poll(timeout=1.0)

            # 定期输出状态
            if time.time() - last_log_time > 5.0:
                elapsed = time.time() - start_time
                logger.info(
                    f"📊 Status: {len(results)} messages, {poll_count} polls, {eof_count} EOF, {elapsed:.1f}s elapsed"
                )
                last_log_time = time.time()

            if msg is None:
                continue

            if msg.error():
                error_code = msg.error().code()

                if error_code == KafkaError._PARTITION_EOF:
                    eof_count += 1

                    # 如果多次 EOF 且没有消息，提前退出
                    if len(results) == 0 and eof_count > len(topics) * 2:
                        logger.info(f"⚠️  Reached EOF on all partitions ({eof_count} EOF messages) with no data")
                        break
                    continue
                error_detail = f"Poll #{poll_count}: ERROR - {msg.error()}"
                logger.info(error_detail)
                continue

            # 成功获取消息
            try:
                # 反序列化消息
                value_bytes = msg.value()
                if not value_bytes:
                    continue

                if self.value_deserializer == "json":
                    try:
                        value = json.loads(value_bytes.decode("utf-8"))
                    except json.JSONDecodeError as json_error:
                        raw_text = value_bytes.decode("utf-8", errors="replace")
                        preview = raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
                        error_detail = f"  JSON decode error: {json_error}. Preview: {preview}"
                        logger.info(error_detail)
                        continue
                else:
                    try:
                        value = value_bytes.decode("utf-8")
                    except UnicodeDecodeError as unicode_error:
                        error_detail = f"  Unicode decode error: {unicode_error}"
                        logger.info(error_detail)
                        continue

                # 提取 JSONPath
                if self.json_path and isinstance(value, dict):
                    try:
                        value = self._extract_json_path(value)
                    except Exception as path_error:
                        logger.info(f"  JSONPath extraction error: {path_error}")
                        continue

                # 处理消息
                processed_data = self._process_message(value)

                # 添加 Kafka 元数据
                if isinstance(processed_data, dict):
                    processed_data.update(
                        {
                            "_kafka_topic": msg.topic(),
                            "_kafka_partition": msg.partition(),
                            "_kafka_offset": msg.offset(),
                            "_kafka_timestamp": msg.timestamp()[1] if msg.timestamp()[0] else None,
                        }
                    )

                    # 确保有 text 和 content 字段用于兼容性
                    if "text" not in processed_data and "content" not in processed_data:
                        text_value = json.dumps(processed_data, ensure_ascii=False, indent=2)
                        processed_data["text"] = text_value
                        processed_data["content"] = text_value
                    elif "text" in processed_data and "content" not in processed_data:
                        processed_data["content"] = processed_data["text"]
                    elif "content" in processed_data and "text" not in processed_data:
                        processed_data["text"] = processed_data["content"]

                # 缓存样本数据
                if len(self._sample_data_cache) < SAMPLE_CACHE_SIZE:
                    self._sample_data_cache.append(processed_data.copy())

                # 创建 Data 对象
                data_obj = Data(data=processed_data)
                results.append(data_obj)

            except Exception as processing_error:
                error_detail = f"  Unexpected error processing message: {processing_error}"
                logger.info(error_detail)
                continue

        elapsed = time.time() - start_time
        logger.info(f"Consumed {len(results)} messages in {elapsed:.2f}s (polls={poll_count}, eof={eof_count})")

        return results

    async def consume_messages(self):
        """智能数据获取：设计时返回样本数据，运行时返回流式数据"""
        try:
            # 检查是否在设计时上下文中（字段分析等）
            is_design_time = self._is_design_time_context()
            if is_design_time:
                logger.info("[KafkaInput] Design-time context detected, returning sample data list")
                sample_data_list = self.get_sample_data()
                return sample_data_list

            # 运行时：重置停止标志
            self._should_stop = False
            self.status = i18n.t("components.input_output.kafka_input.status.connecting")

            # 导入必要库
            try:
                from confluent_kafka import Consumer, KafkaError
            except ImportError as import_err:
                error_msg = i18n.t("components.input_output.kafka_input.errors.kafka_not_installed")
                logger.error(error_msg)
                raise ImportError(error_msg) from import_err

            # 解析主题列表
            topics = [t.strip() for t in self.topics.split(",")]

            # 运行时：使用异步生成器进行流式消费
            logger.info("Starting async streaming mode")

            # 创建一个异步生成器
            async def stream_generator():
                async for data in self._consume_messages_streaming_async():
                    yield data

            return stream_generator()

        except Exception as e:
            error_msg = i18n.t("components.input_output.kafka_input.errors.consume_failed", error=str(e))
            self.status = error_msg
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        finally:
            # 只在运行时关闭consumer
            if not self._is_design_time_context():
                if not self.keep_consumer_alive:
                    self._close_current_consumer()
                else:
                    logger.info("Keeping consumer alive for next execution")

    def consume_data_sync(self) -> list[Data]:
        """同步获取数据，用于设计时字段分析。

        这个方法专门用于设计时的字段分析，返回基于schema的样本数据。
        """
        logger.info("[KafkaInput] Getting data for design-time field analysis")
        return self.get_sample_data()

    def _extract_json_path(self, data: dict) -> Any:
        """Extract data using JSONPath notation."""
        if not self.json_path:
            return data

        path_parts = self.json_path.strip("$.").split(".")
        current = data

        for part in path_parts:
            if isinstance(current, dict):
                current = current.get(part, current)
            else:
                break

        return current

    def _flatten_dict(self, d: dict, parent_key: str, result: dict):
        """Recursively flatten dictionary."""
        for key, value in d.items():
            new_key = f"{parent_key}_{key}" if parent_key else key

            if isinstance(value, dict):
                self._flatten_dict(value, new_key, result)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                # For object arrays, only flatten the first element
                self._flatten_dict(value[0], new_key, result)
            else:
                result[new_key] = value

    def _extract_by_json_path(self, data: dict, json_path: str) -> Any:
        """Extract data from dictionary using JSON Path notation."""
        if not json_path or not json_path.startswith("$"):
            return data

        # Remove '$.' prefix and split path
        path_parts = json_path[2:].split(".") if json_path.startswith("$.") else json_path[1:].split(".")
        # Filter out empty parts
        path_parts = [p for p in path_parts if p]

        current = data

        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _extract_fields_from_schema(self, message_value: Any) -> dict:
        """Extract fields based on message schema definition.

        Priority: Schema fields > Actual message content
        优先使用schema定义的字段，如果schema为空才使用默认value字段
        """
        # 如果没有schema定义，使用默认value字段
        if not self.message_schema:
            return {"value": message_value}

        result = {}
        has_valid_fields = False

        for schema_row in self.message_schema:
            field_name = schema_row.get("field_name")
            if not field_name:
                continue

            field_type = schema_row.get("field_type", "string")
            json_path = schema_row.get("json_path", "")
            required = schema_row.get("required", False)

            # 尝试从消息中提取值
            extracted_value = None

            if isinstance(message_value, dict):
                if json_path:
                    # 如果提供了json_path，使用json_path提取
                    extracted_value = self._extract_by_json_path(message_value, json_path)
                elif field_name in message_value:
                    # 如果没有json_path但字段名在dict中存在，直接提取
                    extracted_value = message_value[field_name]
                    logger.debug(f"[KafkaInput] Extracted field '{field_name}' directly from message")

            # 如果提取失败或消息不是dict，特殊处理'value'字段
            if extracted_value is None:
                if field_name == "value":
                    # 对于'value'字段，使用消息本身的值
                    result[field_name] = message_value
                    has_valid_fields = True
                elif required:
                    # 必填字段但无法提取，设置为None
                    result[field_name] = None
                    logger.debug(f"[KafkaInput] Required field '{field_name}' set to None (not found in message)")
                # 可选字段且无法提取，跳过
            else:
                # 成功提取到值
                result[field_name] = extracted_value
                has_valid_fields = True

        # 如果schema没有提取到任何有效字段，回退到使用value字段
        if not has_valid_fields:
            logger.warning("[KafkaInput] Schema defined but no valid fields extracted, using default 'value' field")
            result = {"value": message_value}

        return result

    def _process_message(self, message_value: Any) -> dict:
        """Process message based on field extraction mode and output format."""
        # First, handle field extraction based on mode
        if self.field_extraction_mode == "schema_only":
            if self.message_schema:
                processed = self._extract_fields_from_schema(message_value)
            else:
                logger.info(i18n.t("components.input_output.kafka_input.logs.schema_mode_no_schema"))
                processed = message_value if isinstance(message_value, dict) else {"value": message_value}

        elif self.field_extraction_mode == "flatten_all":
            # Flatten everything
            if isinstance(message_value, dict):
                processed = {}
                self._flatten_dict(message_value, "", processed)
            else:
                processed = {"value": message_value}

        elif self.message_schema:
            # Use schema if defined
            processed = self._extract_fields_from_schema(message_value)
        # Fallback to flatten all
        elif isinstance(message_value, dict):
            processed = {}
            self._flatten_dict(message_value, "", processed)
        else:
            processed = {"value": message_value}

        # Then handle output format
        if self.output_format == "flattened":
            # For flattened output, ensure single level
            if isinstance(processed, dict):
                result = {}
                self._flatten_dict(processed, "", result)
                return result
            return {"value": processed}

        # Raw output (preserves structure from schema or flatten_all)
        result = processed if isinstance(processed, dict) else {"value": processed}

        # 确保结果是字典类型
        if not isinstance(result, dict):
            result = {"value": result}

        return result

    def test_connection(self) -> dict:
        """Test Kafka connection and provide diagnostic information."""
        try:
            self.status = i18n.t("components.input_output.kafka_input.status.testing_connection")

            # Import confluent-kafka
            try:
                from confluent_kafka import Consumer, KafkaError
            except ImportError as import_err:
                return {
                    "success": False,
                    "error": i18n.t("components.input_output.kafka_input.errors.kafka_not_installed"),
                    "details": str(import_err),
                }

            # Parse topics
            topics = [t.strip() for t in self.topics.split(",")]

            # Configure consumer for testing
            consumer_config = {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": f"{self.group_id}_test",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "session.timeout.ms": 10000,
                "request.timeout.ms": 10000,
            }

            # Add SASL authentication if provided
            if self.sasl_username and self.sasl_password:
                consumer_config.update(
                    {
                        "security.protocol": "SASL_PLAINTEXT",
                        "sasl.mechanism": "PLAIN",
                        "sasl.username": self.sasl_username,
                        "sasl.password": self.sasl_password,
                    }
                )

            diagnostic_info = {
                "bootstrap_servers": self.bootstrap_servers,
                "topics": topics,
                "group_id": self.group_id,
                "sasl_enabled": bool(self.sasl_username and self.sasl_password),
            }

            # Test 1: Create consumer
            try:
                consumer = Consumer(consumer_config)
                diagnostic_info["consumer_creation"] = "success"
            except Exception as e:
                diagnostic_info["consumer_creation"] = "failed"
                return {
                    "success": False,
                    "error": f"Failed to create consumer: {e!s}",
                    "diagnostic": diagnostic_info,
                }

            # Test 2: Get metadata
            try:
                cluster_metadata = consumer.list_topics(timeout=5.0)
                diagnostic_info["cluster_metadata"] = {
                    "brokers": len(cluster_metadata.brokers),
                    "topics": len(cluster_metadata.topics),
                    "cluster_id": getattr(cluster_metadata, "cluster_id", "unknown"),
                }
            except Exception as e:
                consumer.close()
                diagnostic_info["cluster_metadata"] = "failed"
                return {
                    "success": False,
                    "error": f"Failed to get cluster metadata: {e!s}",
                    "diagnostic": diagnostic_info,
                }

            # Test 3: Check if topics exist
            topic_metadata = {}
            missing_topics = []
            for topic in topics:
                try:
                    topic_info = cluster_metadata.topics.get(topic)
                    if topic_info:
                        topic_metadata[topic] = {
                            "partitions": len(topic_info.partitions),
                            "replicas": topic_info.partitions[0].replicas if topic_info.partitions else [],
                        }
                    else:
                        missing_topics.append(topic)
                except Exception as e:
                    topic_metadata[topic] = {"error": str(e)}

            diagnostic_info["topic_metadata"] = topic_metadata
            diagnostic_info["missing_topics"] = missing_topics

            if missing_topics:
                consumer.close()
                return {
                    "success": False,
                    "error": f"Topics not found: {', '.join(missing_topics)}",
                    "diagnostic": diagnostic_info,
                }

            # Test 4: Subscribe to topics
            try:
                consumer.subscribe(topics)
                diagnostic_info["subscription"] = "success"
            except Exception as e:
                consumer.close()
                diagnostic_info["subscription"] = "failed"
                return {
                    "success": False,
                    "error": f"Failed to subscribe to topics: {e!s}",
                    "diagnostic": diagnostic_info,
                }

            # Test 5: Poll for messages (brief test)
            try:
                message_count = 0
                start_time = time.time()
                while time.time() - start_time < 3.0:  # Test for 3 seconds
                    msg = consumer.poll(timeout=1.0)
                    if msg is None:
                        continue
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            continue
                        diagnostic_info["poll_error"] = str(msg.error())
                        break
                    message_count += 1
                    if message_count >= 5:  # Found some messages, connection is working
                        break

                diagnostic_info["messages_found"] = message_count
                diagnostic_info["poll_test"] = "success"
            except Exception as e:
                diagnostic_info["poll_test"] = "failed"
                diagnostic_info["poll_error"] = str(e)

            consumer.close()

            # Determine overall success
            success = (
                diagnostic_info.get("consumer_creation") == "success"
                and diagnostic_info.get("cluster_metadata") != "failed"
                and not missing_topics
                and diagnostic_info.get("subscription") == "success"
            )

            return {
                "success": success,
                "message": "Connection successful" if success else "Connection test completed with issues",
                "diagnostic": diagnostic_info,
                "recommendations": self._get_connection_recommendations(diagnostic_info),
            }

        except Exception as e:
            return {"success": False, "error": f"Connection test failed: {e!s}", "diagnostic": {"error": str(e)}}

    def _get_connection_recommendations(self, diagnostic: dict) -> list[str]:
        """Get connection recommendations based on diagnostic information."""
        recommendations = []

        if diagnostic.get("consumer_creation") == "failed":
            recommendations.append("Check bootstrap servers format (e.g., 'localhost:9092')")
            recommendations.append("Verify Kafka cluster is running")

        if diagnostic.get("missing_topics"):
            recommendations.append(f"Create missing topics: {', '.join(diagnostic['missing_topics'])}")
            recommendations.append("Check topic spelling and permissions")

        if diagnostic.get("sasl_enabled") and diagnostic.get("subscription") == "failed":
            recommendations.append("Verify SASL username and password")
            recommendations.append("Check if SASL authentication is properly configured on Kafka broker")

        if diagnostic.get("messages_found", 0) == 0 and diagnostic.get("poll_test") == "success":
            recommendations.append("Try setting 'Reset Offsets' to True to read from beginning")
            recommendations.append("Send test messages to the topics")
            recommendations.append("Check if auto_offset_reset is set to 'earliest'")

        return recommendations

    def get_sample_data(self) -> list[Data]:
        """Get cached sample data for downstream component field discovery."""
        if self._sample_data_cache:
            return [Data(data=sample) for sample in self._sample_data_cache]

        # Auto-populate schema if empty (for design-time discovery)
        if not self.message_schema:
            logger.info("[KafkaInput] No schema defined, creating example schema for field discovery")
            self.message_schema = [
                {"field_name": "id", "field_type": "string", "required": True, "json_path": "", "description": "Unique identifier"},
                {"field_name": "name", "field_type": "string", "required": True, "json_path": "", "description": "Entity name"},
                {"field_name": "value", "field_type": "float", "required": False, "json_path": "", "description": "Numeric value"},
                {"field_name": "timestamp", "field_type": "timestamp", "required": True, "json_path": "", "description": "Event timestamp"}
            ]
            logger.info(f"[KafkaInput] Created example schema with {len(self.message_schema)} fields")

        # Generate sample data based on schema if available
        if self.message_schema:
            logger.info(f"[KafkaInput] Generating sample data from schema with {len(self.message_schema)} fields")

            # Create sample data based on user-defined schema
            sample_data = {}
            valid_fields_found = False

            for field in self.message_schema:
                # Debug field structure
                logger.debug(f"[KafkaInput] Processing field: {field}")

                field_name = field.get("field_name", "")
                field_type = field.get("field_type", "string")
                is_required = field.get("required", False)

                # Skip empty field names (only if not required)
                if not field_name or field_name.strip() == "":
                    if is_required:
                        logger.warning("[KafkaInput] Required field has empty name, using placeholder")
                        field_name = "required_field"
                    else:
                        logger.debug("[KafkaInput] Skipping empty field name")
                        continue

                logger.debug(f"[KafkaInput] Adding field '{field_name}' with type '{field_type}', required: {is_required}")

                # Generate sample value based on type
                if field_type == "string":
                    sample_data[field_name] = f"sample_{field_name}"
                elif field_type == "int":
                    sample_data[field_name] = 0
                elif field_type == "float":
                    sample_data[field_name] = 0.0
                elif field_type == "bool":
                    sample_data[field_name] = True
                elif field_type == "json":
                    sample_data[field_name] = {"nested": "value"}
                elif field_type == "timestamp":
                    sample_data[field_name] = "2024-01-01T00:00:00Z"
                else:
                    sample_data[field_name] = f"sample_{field_name}"

                valid_fields_found = True

            # If no valid fields were found, provide default sample data
            if not valid_fields_found:
                logger.warning("[KafkaInput] No valid schema fields found, providing default sample data")
                sample_data = {
                    "id": "sample_id",
                    "name": "sample_name",
                    "value": "sample_value",
                    "timestamp": "2024-01-01T00:00:00Z"
                }

            # Add Kafka metadata
            sample_data.update({
                "_kafka_topic": self.topics.split(",")[0] if self.topics else "sample_topic",
                "_kafka_partition": 0,
                "_kafka_offset": 0,
                "_kafka_timestamp": "2024-01-01T00:00:00Z"
            })

            logger.info(f"[KafkaInput] Generated sample data: {sample_data}")
            return [Data(data=sample_data)]

        # If no schema, return example structure
        example_data = {
            "_kafka_topic": self.topics.split(",")[0] if self.topics else "sample_topic",
            "_kafka_partition": 0,
            "_kafka_offset": 0,
            "_kafka_timestamp": "2024-01-01T00:00:00Z"
        }

        # Adjust example based on output format
        if self.output_format == "flattened":
            # Flattened example with common fields
            example_data.update({
                "id": "sample_id",
                "name": "sample_name",
                "value": "sample_value",
                "timestamp": "2024-01-01T00:00:00Z"
            })
            return [Data(data=example_data)]

        # Raw structure example
        return [Data(data={"value": "sample_data", **example_data})]

    def get_consumer_info(self) -> Data:
        """Get Kafka consumer information."""
        info = {
            "bootstrap_servers": self.bootstrap_servers,
            "topics": self.topics,
            "group_id": self.group_id,
            "max_messages": self.max_messages,
            "timeout_ms": self.timeout_ms,
            "auto_offset_reset": self.auto_offset_reset,
            "output_format": self.output_format,
            "field_extraction_mode": self.field_extraction_mode,
            "batch_size": self.batch_size,
            "auto_commit": self.auto_commit,
            "value_deserializer": self.value_deserializer,
            "json_path": self.json_path if self.json_path else None,
            "sasl_enabled": bool(self.sasl_username and self.sasl_password),
            "schema_defined": bool(self.message_schema),
            "schema_fields": len(self.message_schema) if self.message_schema else 0,
            "debug_mode": self.debug_mode,
            "reset_offsets": self.reset_offsets,
        }
        return Data(data=info)

    def update_build_config(
        self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None, action: str | None = None
    ) -> dict[str, Any]:
        """Update build config based on user actions."""
        if field_name == "message_schema" and field_value == "auto_detect_schema":
            # Auto-detect schema from sample messages
            try:
                sample_schema = self._auto_detect_schema_from_samples()
                if sample_schema:
                    build_config["message_schema"]["value"] = sample_schema
                    self.status = i18n.t(
                        "components.input_output.kafka_input.status.schema_detected", fields=len(sample_schema)
                    )
                else:
                    self.status = i18n.t("components.input_output.kafka_input.status.no_schema_detected")
            except Exception as e:
                error_msg = i18n.t("components.input_output.kafka_input.errors.schema_detection_failed", error=str(e))
                self.status = error_msg
                logger.info(f"Schema detection failed: {e}")

        return build_config

    def _auto_detect_schema_from_samples(self) -> list[dict]:
        """Auto-detect schema from cached sample messages."""
        if not self._sample_data_cache:
            # Try to get sample messages
            try:
                # Create a temporary consumer to fetch samples
                from confluent_kafka import Consumer, KafkaError

                consumer_config = {
                    "bootstrap.servers": self.bootstrap_servers,
                    "group.id": f"{self.group_id}_schema_detection",
                    "auto.offset.reset": "latest",
                    "enable.auto.commit": False,
                }

                if self.sasl_username and self.sasl_password:
                    consumer_config.update(
                        {
                            "security.protocol": "SASL_PLAINTEXT",
                            "sasl.mechanism": "PLAIN",
                            "sasl.username": self.sasl_username,
                            "sasl.password": self.sasl_password,
                        }
                    )

                consumer = Consumer(consumer_config)
                topics = [t.strip() for t in self.topics.split(",")]
                consumer.subscribe(topics)

                # Try to get a few messages
                samples = []
                for _ in range(5):  # Try up to 5 messages
                    try:
                        message = consumer.poll(timeout=2.0)
                        if message is None:
                            continue

                        if message.error():
                            if message.error().code() == KafkaError._PARTITION_EOF:
                                continue
                            logger.info(f"Error fetching sample: {message.error()}")
                            continue

                        # Deserialize message
                        value_bytes = message.value()
                        if self.value_deserializer == "json":
                            value = json.loads(value_bytes.decode("utf-8"))
                        else:
                            value = value_bytes.decode("utf-8")

                        samples.append(value)
                        if len(samples) >= 3:  # Get at least 3 samples
                            break
                    except Exception as e:
                        logger.info(f"Error processing sample message: {e}")
                        continue

                consumer.close()

                # Update sample cache
                for sample in samples:
                    if isinstance(sample, dict):
                        flattened = {}
                        self._flatten_dict(sample, "", flattened)
                        self._sample_data_cache.append(flattened)

            except Exception as e:
                logger.info(f"Failed to fetch sample messages: {e}")
                return []

        # Analyze sample data to create schema
        if not self._sample_data_cache:
            return []

        return self._analyze_sample_data_for_schema(self._sample_data_cache)

    def _analyze_sample_data_for_schema(self, samples: list[dict]) -> list[dict]:
        """Analyze sample data to create schema definition."""
        if not samples:
            return []

        # Collect all possible fields and their types
        field_info = {}

        for sample in samples:
            if isinstance(sample, dict):
                for field_name, value in sample.items():
                    if field_name not in field_info:
                        field_info[field_name] = {"count": 0, "values": [], "types": set(), "examples": []}

                    field_info[field_name]["count"] += 1
                    field_info[field_name]["values"].append(value)
                    field_info[field_name]["types"].add(type(value).__name__)

                    # Keep a few examples
                    if len(field_info[field_name]["examples"]) < 3:
                        field_info[field_name]["examples"].append(str(value))

        # Generate schema rows
        schema = []
        total_samples = len(samples)

        for field_name, info in field_info.items():
            # Determine field type
            types = info["types"]
            field_type = "string"  # default

            if len(types) == 1:
                single_type = list(types)[0]
                if single_type == "int":
                    field_type = "int"
                elif single_type == "float":
                    field_type = "float"
                elif single_type == "bool":
                    field_type = "bool"
                elif single_type == "dict":
                    field_type = "json"

            # Determine if required (present in all samples)
            required = info["count"] == total_samples

            # Generate JSON Path (assuming flat structure for auto-detect)
            json_path = f"$.{field_name}"

            # Generate description
            examples_str = ", ".join(info["examples"][:2])
            if len(info["examples"]) > 2:
                examples_str += f" (and {len(info['examples']) - 2} more)"
            description = f"Auto-detected from {info['count']} samples. Examples: {examples_str}"

            schema_row = {
                "field_name": field_name,
                "field_type": field_type,
                "json_path": json_path,
                "required": required,
                "description": description,
            }

            schema.append(schema_row)

        # Sort by frequency (most common first) then by name
        schema.sort(key=lambda x: (-field_info[x["field_name"]]["count"], x["field_name"]))

        return schema

    def _consume_messages_batch(self) -> list[Data]:
        """批量消费 Kafka 消息（原有逻辑）"""
        # 导入 confluent-kafka
        try:
            from confluent_kafka import Consumer, KafkaError  # noqa: F401
        except ImportError as import_err:
            error_msg = i18n.t("components.input_output.kafka_input.errors.kafka_not_installed")
            logger.error(error_msg)
            raise ImportError(error_msg) from import_err

        # 解析主题列表
        topics = [t.strip() for t in self.topics.split(",")]

        # 1. 如果不保持 Consumer 活跃，关闭旧的
        if not self.keep_consumer_alive:
            self._close_current_consumer()

        # 2. 复用或创建 Consumer
        if self._current_consumer is None:
            consumer = self._create_consumer()
            self._current_consumer = consumer
        else:
            consumer = self._current_consumer
            logger.info("Reusing existing consumer")

        # 3. 记录订阅信息
        self._log_subscription_info(consumer, topics)

        # 4. 订阅主题
        logger.info(f"Subscribing to topics: {topics}...")
        consumer.subscribe(topics)
        logger.info("✓ Subscribed successfully")

        # 5. 等待分区分配
        self._wait_for_assignment(consumer)

        # 6. 记录分区分配详情
        self._log_partition_assignment(consumer)

        # 7. 轮询消息
        self.status = i18n.t("components.input_output.kafka_input.status.consuming")
        results = self._poll_messages(consumer, topics)

        # 8. 根据配置决定是否关闭 Consumer
        if not self.keep_consumer_alive:
            self._close_current_consumer()
        else:
            logger.info("Keeping consumer alive for next execution")

        # 9. 返回结果
        if results:
            self.status = i18n.t("components.input_output.kafka_input.status.success", messages=len(results))
        else:
            self.status = i18n.t("components.input_output.kafka_input.status.no_messages_found")
            logger.info("")
            logger.info("💡 Troubleshooting:")
            logger.info("  1. Check if there are messages in the topic")
            logger.info("  2. Try enabling 'Reset Offsets' option")
            logger.info("  3. Verify 'Auto Offset Reset' is set to 'earliest'")
            logger.info("  4. Check Consumer Lag using kafka-consumer-groups command")

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return results

    def _consume_messages_streaming(self) -> Generator[Data, None, None]:
        """流式消费 Kafka 消息 - 接收一条立即 yield 一条"""
        from confluent_kafka import KafkaError

        # 解析主题列表
        topics = [t.strip() for t in self.topics.split(",")]

        try:
            # 1. 如果不保持 Consumer 活跃，关闭旧的
            if not self.keep_consumer_alive:
                self._close_current_consumer()

            # 2. 复用或创建 Consumer
            if self._current_consumer is None:
                consumer = self._create_consumer()
                self._current_consumer = consumer
            else:
                consumer = self._current_consumer
                logger.info("Reusing existing consumer")

            # 3. 记录订阅信息
            self._log_subscription_info(consumer, topics)

            # 4. 订阅主题
            logger.info(f"Subscribing to topics: {topics}...")
            consumer.subscribe(topics)
            logger.info("✓ Subscribed successfully")

            # 5. 等待分区分配
            self._wait_for_assignment(consumer)

            # 6. 记录分区分配详情
            self._log_partition_assignment(consumer)

            # 7. 开始流式轮询
            self.status = i18n.t("components.input_output.kafka_input.status.streaming")
            logger.info("Starting streaming consumption...")

            message_count = 0
            poll_timeout = 1.0  # 1秒超时，快速响应停止信号

            while not self._should_stop:
                try:
                    # 检查停止标志
                    if self._should_stop:
                        logger.info("Stop signal detected, exiting")
                        break

                    # 轮询单条消息
                    msg = consumer.poll(timeout=poll_timeout)

                    if msg is None:
                        continue

                    if msg.error():
                        error_code = msg.error().code()
                        if error_code == KafkaError._PARTITION_EOF:
                            continue
                        logger.warning(f"Kafka error: {msg.error()}")
                        continue

                    # 成功获取消息

                    try:
                        # 反序列化消息
                        value_bytes = msg.value()
                        if not value_bytes:
                            continue

                        if self.value_deserializer == "json":
                            try:
                                value = json.loads(value_bytes.decode("utf-8"))
                            except json.JSONDecodeError as json_error:
                                logger.warning(f"JSON decode error: {json_error}")
                                continue
                        else:
                            try:
                                value = value_bytes.decode("utf-8")
                            except UnicodeDecodeError as unicode_error:
                                logger.warning(f"Unicode decode error: {unicode_error}")
                                continue

                        # 提取 JSONPath
                        if self.json_path and isinstance(value, dict):
                            try:
                                value = self._extract_json_path(value)
                            except Exception as path_error:
                                logger.warning(f"JSONPath extraction error: {path_error}")
                                continue

                        # 处理消息
                        processed_data = self._process_message(value)

                        # 添加 Kafka 元数据
                        if isinstance(processed_data, dict):
                            processed_data.update(
                                {
                                    "_kafka_topic": msg.topic(),
                                    "_kafka_partition": msg.partition(),
                                    "_kafka_offset": msg.offset(),
                                    "_kafka_timestamp": msg.timestamp()[1] if msg.timestamp()[0] else None,
                                }
                            )

                            # 确保有 text 和 content 字段用于兼容性
                            if "text" not in processed_data and "content" not in processed_data:
                                text_value = json.dumps(processed_data, ensure_ascii=False, indent=2)
                                processed_data["text"] = text_value
                                processed_data["content"] = text_value
                            elif "text" in processed_data and "content" not in processed_data:
                                processed_data["content"] = processed_data["text"]
                            elif "content" in processed_data and "text" not in processed_data:
                                processed_data["text"] = processed_data["content"]

                        # 缓存样本数据
                        if len(self._sample_data_cache) < SAMPLE_CACHE_SIZE:
                            self._sample_data_cache.append(processed_data.copy())

                        # 创建 Data 对象并立即 yield
                        data_obj = Data(data=processed_data)
                        message_count += 1

                        # 更新状态
                        if message_count % 10 == 0:
                            self.status = f"📊 Streaming: {message_count} messages"
                            logger.info(f"Streamed {message_count} messages so far")

                        yield data_obj

                    except Exception as processing_error:
                        logger.error(f"Error processing message: {processing_error}")
                        continue

                except KeyboardInterrupt:
                    logger.info("Streaming interrupted by user")
                    self._should_stop = True
                    break
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    # 继续运行，不因单个错误而中断
                    continue

            # 流式消费结束
            logger.info(f"Streaming completed: {message_count} messages")
            self.status = f"Streaming completed: {message_count} messages"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self.status = f"Streaming error: {e}"
            raise
        finally:
            # 注意：不在这里关闭 consumer，由 consume_messages 的 finally 块处理
            pass

    async def _consume_messages_streaming_async(self) -> AsyncGenerator[Data, None]:
        """异步流式消费 Kafka 消息 - 接收一条立即 yield 一条（真正非阻塞）"""
        import asyncio

        from confluent_kafka import KafkaError

        # 解析主题列表
        topics = [t.strip() for t in self.topics.split(",")]

        try:
            # 1. 如果不保持 Consumer 活跃，关闭旧的
            if not self.keep_consumer_alive:
                self._close_current_consumer()

            # 2. 复用或创建 Consumer
            if self._current_consumer is None:
                consumer = self._create_consumer()
                self._current_consumer = consumer
            else:
                consumer = self._current_consumer
                logger.info("Reusing existing consumer")

            # 3. 记录订阅信息
            self._log_subscription_info(consumer, topics)

            # 4. 订阅主题
            logger.info(f"Subscribing to topics: {topics}...")
            consumer.subscribe(topics)
            logger.info("✓ Subscribed successfully")

            # 5. 等待分区分配（在线程池中执行）
            await asyncio.to_thread(self._wait_for_assignment, consumer)

            # 6. 记录分区分配详情
            self._log_partition_assignment(consumer)

            # 7. 开始流式轮询
            self.status = i18n.t("components.input_output.kafka_input.status.streaming")
            logger.info("Starting async streaming consumption...")

            message_count = 0
            poll_timeout = 1.0  # 1秒超时，快速响应停止信号

            while not self._should_stop:
                try:
                    # 检查停止标志
                    if self._should_stop:
                        logger.info("Stop signal detected, exiting")
                        break

                    # ✅ 在线程池中执行阻塞的 poll 操作
                    msg = await asyncio.to_thread(consumer.poll, poll_timeout)

                    if msg is None:
                        # ✅ 让出控制权，保持 UI 响应
                        await asyncio.sleep(0)
                        continue

                    if msg.error():
                        error_code = msg.error().code()
                        if error_code == KafkaError._PARTITION_EOF:
                            await asyncio.sleep(0)
                            continue
                        logger.warning(f"Kafka error: {msg.error()}")
                        await asyncio.sleep(0)
                        continue

                    # 成功获取消息

                    try:
                        # 反序列化消息
                        value_bytes = msg.value()
                        if not value_bytes:
                            await asyncio.sleep(0)
                            continue

                        if self.value_deserializer == "json":
                            try:
                                value = json.loads(value_bytes.decode("utf-8"))
                            except json.JSONDecodeError as json_error:
                                logger.warning(f"JSON decode error: {json_error}")
                                await asyncio.sleep(0)
                                continue
                        else:
                            try:
                                value = value_bytes.decode("utf-8")
                            except UnicodeDecodeError as unicode_error:
                                logger.warning(f"Unicode decode error: {unicode_error}")
                                await asyncio.sleep(0)
                                continue

                        # 提取 JSONPath
                        if self.json_path and isinstance(value, dict):
                            try:
                                value = self._extract_json_path(value)
                            except Exception as path_error:
                                logger.warning(f"JSONPath extraction error: {path_error}")
                                await asyncio.sleep(0)
                                continue

                        # 处理消息
                        processed_data = self._process_message(value)

                        # 添加 Kafka 元数据
                        if isinstance(processed_data, dict):
                            processed_data.update(
                                {
                                    "_kafka_topic": msg.topic(),
                                    "_kafka_partition": msg.partition(),
                                    "_kafka_offset": msg.offset(),
                                    "_kafka_timestamp": msg.timestamp()[1] if msg.timestamp()[0] else None,
                                }
                            )

                            # 确保有 text 和 content 字段用于兼容性
                            if "text" not in processed_data and "content" not in processed_data:
                                text_value = json.dumps(processed_data, ensure_ascii=False, indent=2)
                                processed_data["text"] = text_value
                                processed_data["content"] = text_value
                            elif "text" in processed_data and "content" not in processed_data:
                                processed_data["content"] = processed_data["text"]
                            elif "content" in processed_data and "text" not in processed_data:
                                processed_data["text"] = processed_data["content"]

                        # 缓存样本数据
                        if len(self._sample_data_cache) < SAMPLE_CACHE_SIZE:
                            self._sample_data_cache.append(processed_data.copy())

                        # 创建 Data 对象并立即 yield
                        data_obj = Data(data=processed_data)
                        message_count += 1

                        # 更新状态
                        if message_count % 10 == 0:
                            self.status = f"📊 Streaming: {message_count} messages"
                            logger.info(f"Streamed {message_count} messages so far")

                        yield data_obj

                        # ✅ 让出控制权，允许其他任务运行
                        await asyncio.sleep(0)

                    except Exception as processing_error:
                        logger.error(f"Error processing message: {processing_error}")
                        await asyncio.sleep(0)
                        continue

                except KeyboardInterrupt:
                    logger.info("Streaming interrupted by user")
                    self._should_stop = True
                    break
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    # 继续运行，不因单个错误而中断
                    await asyncio.sleep(0)
                    continue

            # 流式消费结束
            logger.info(f"Async streaming completed: {message_count} messages")
            self.status = f"Streaming completed: {message_count} messages"

        except Exception as e:
            logger.error(f"Async streaming error: {e}")
            self.status = f"Streaming error: {e}"
            raise
        finally:
            # 注意：不在这里关闭 consumer，由 consume_messages 的 finally 块处理
            pass
