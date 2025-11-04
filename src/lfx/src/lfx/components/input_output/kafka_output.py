import json
import asyncio
from typing import Any, Dict, List, Optional

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    TableInput,
)
from lfx.log.logger import logger
from lfx.schema import Data


class ETLKafkaOutputComponent(Component):
    display_name = i18n.t("components.input_output.kafka_output.display_name")
    description = i18n.t("components.input_output.kafka_output.description")
    icon = "send"
    name = "ETLKafkaOutput"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._producer = None

    def __del__(self):
        """Cleanup when component is destroyed."""
        try:
            if self._producer:
                self._producer.flush(timeout=5)
                self._producer = None
                logger.info("Component destroyed, producer flushed")
        except Exception:
            pass  # Ignore errors during cleanup

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.input_output.kafka_output.data_input.display_name"),
            info=i18n.t("components.input_output.kafka_output.data_input.info"),
            is_list=True,
            required=True,
        ),
        MessageTextInput(
            name="bootstrap_servers",
            display_name=i18n.t("components.input_output.kafka_output.bootstrap_servers.display_name"),
            info=i18n.t("components.input_output.kafka_output.bootstrap_servers.info"),
            required=True,
            placeholder="localhost:9092",
        ),
        MessageTextInput(
            name="topic",
            display_name=i18n.t("components.input_output.kafka_output.topic.display_name"),
            info=i18n.t("components.input_output.kafka_output.topic.info"),
            required=True,
            placeholder="output-topic",
        ),
        MessageTextInput(
            name="key_field",
            display_name=i18n.t("components.input_output.kafka_output.key_field.display_name"),
            info=i18n.t("components.input_output.kafka_output.key_field.info"),
            placeholder="id",
            advanced=True,
        ),
        DropdownInput(
            name="value_serializer",
            display_name=i18n.t("components.input_output.kafka_output.value_serializer.display_name"),
            info=i18n.t("components.input_output.kafka_output.value_serializer.info"),
            options=["json", "string"],
            value="json",
        ),
        MessageTextInput(
            name="partition_key",
            display_name=i18n.t("components.input_output.kafka_output.partition_key.display_name"),
            info=i18n.t("components.input_output.kafka_output.partition_key.info"),
            placeholder="",
            advanced=True,
        ),
        TableInput(
            name="headers",
            display_name=i18n.t("components.input_output.kafka_output.headers.display_name"),
            info=i18n.t("components.input_output.kafka_output.headers.info"),
            table_schema=[
                {"name": "key", "display_name": "Header Key", "type": "str"},
                {"name": "value", "display_name": "Header Value", "type": "str"},
            ],
            value=[],
            advanced=True,
        ),
        DropdownInput(
            name="compression_type",
            display_name=i18n.t("components.input_output.kafka_output.compression_type.display_name"),
            info=i18n.t("components.input_output.kafka_output.compression_type.info"),
            options=["none", "gzip", "snappy", "lz4"],
            value="none",
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t("components.input_output.kafka_output.batch_size.display_name"),
            info=i18n.t("components.input_output.kafka_output.batch_size.info"),
            value=100,
            advanced=True,
        ),
        IntInput(
            name="timeout_ms",
            display_name=i18n.t("components.input_output.kafka_output.timeout_ms.display_name"),
            info=i18n.t("components.input_output.kafka_output.timeout_ms.info"),
            value=30000,
            advanced=True,
        ),
        DropdownInput(
            name="acks",
            display_name=i18n.t("components.input_output.kafka_output.acks.display_name"),
            info=i18n.t("components.input_output.kafka_output.acks.info"),
            options=["0", "1", "all"],
            value="1",
            advanced=True,
        ),
        IntInput(
            name="retries",
            display_name=i18n.t("components.input_output.kafka_output.retries.display_name"),
            info=i18n.t("components.input_output.kafka_output.retries.info"),
            value=3,
            advanced=True,
        ),
        BoolInput(
            name="send_as_batch",
            display_name=i18n.t("components.input_output.kafka_output.send_as_batch.display_name"),
            info=i18n.t("components.input_output.kafka_output.send_as_batch.info"),
            value=True,
            advanced=True,
        ),
        MessageTextInput(
            name="sasl_username",
            display_name=i18n.t("components.input_output.kafka_output.sasl_username.display_name"),
            info=i18n.t("components.input_output.kafka_output.sasl_username.info"),
            advanced=True,
        ),
        SecretStrInput(
            name="sasl_password",
            display_name=i18n.t("components.input_output.kafka_output.sasl_password.display_name"),
            info=i18n.t("components.input_output.kafka_output.sasl_password.info"),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="result",
            display_name=i18n.t("components.input_output.kafka_output.outputs.result.display_name"),
            method="send_to_kafka",
        ),
        Output(
            name="producer_info",
            display_name=i18n.t("components.input_output.kafka_output.outputs.producer_info.display_name"),
            method="get_producer_info",
        ),
    ]

    def _create_producer(self):
        """Create Kafka producer with configuration."""
        try:
            from confluent_kafka import Producer
        except ImportError as import_err:
            error_msg = i18n.t("components.input_output.kafka_output.errors.kafka_not_installed")
            logger.error(error_msg)
            raise ImportError(error_msg) from import_err

        # Configure producer
        producer_config = {
            "bootstrap.servers": self.bootstrap_servers,
            "acks": self.acks,
            "retries": self.retries,
            "delivery.timeout.ms": self.timeout_ms,
            "batch.size": self.batch_size * 1024,  # Convert to bytes
            "linger.ms": 10,  # Wait up to 10ms for batching
            "queue.buffering.max.messages": 10000,
            "queue.buffering.max.kbytes": 102400,  # 100MB
            "socket.send.buffer.bytes": 102400,
        }

        # Add compression
        if self.compression_type != "none":
            producer_config["compression.type"] = self.compression_type

        # Add SASL authentication
        if self.sasl_username and self.sasl_password:
            producer_config.update(
                {
                    "security.protocol": "SASL_PLAINTEXT",
                    "sasl.mechanism": "PLAIN",
                    "sasl.username": self.sasl_username,
                    "sasl.password": self.sasl_password,
                }
            )

        logger.debug(f"Producer config: servers={self.bootstrap_servers}, topic={self.topic}")

        producer = Producer(producer_config)
        logger.info("Kafka producer created successfully")
        return producer

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value based on configured serializer."""
        if self.value_serializer == "json":
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False).encode("utf-8")
            else:
                return json.dumps({"value": value}, ensure_ascii=False).encode("utf-8")
        else:  # string
            if isinstance(value, str):
                return value.encode("utf-8")
            else:
                return str(value).encode("utf-8")

    def _extract_key(self, data: Dict[str, Any]) -> str:
        """Extract message key from data."""
        if not self.key_field:
            return None

        if self.key_field in data:
            key_value = data[self.key_field]
            return str(key_value) if key_value is not None else None

        return None

    def _delivery_report(self, err, msg):
        """Delivery report callback."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    async def send_to_kafka(self) -> Data:
        """Send data to Kafka topic."""
        try:
            self.status = i18n.t("components.input_output.kafka_output.status.sending")

            if not self.data_input:
                raise ValueError(i18n.t("components.input_output.kafka_output.errors.no_data"))

            # Parse headers
            headers = {}
            if self.headers:
                for header in self.headers:
                    key = header.get("key")
                    value = header.get("value")
                    if key and value:
                        headers[key] = value

            # Extract data from Data objects
            data_list = []
            for data_obj in self.data_input:
                if hasattr(data_obj, "data"):
                    data_list.append(data_obj.data)
                else:
                    data_list.append(data_obj)

            success_count = 0
            error_count = 0
            total_messages = len(data_list)

            # Create producer
            if self._producer is None:
                self._producer = self._create_producer()

            producer = self._producer

            if self.send_as_batch:
                # Send in batches
                for i in range(0, len(data_list), self.batch_size):
                    batch = data_list[i : i + self.batch_size]
                    batch_success = await self._send_batch(producer, batch, headers)
                    success_count += batch_success
                    error_count += len(batch) - batch_success
            else:
                # Send individually
                for data_item in data_list:
                    try:
                        await self._send_single_message(producer, data_item, headers)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")
                        error_count += 1

            # Flush producer to ensure all messages are sent
            producer.flush(timeout=5)

            result_info = {
                "topic": self.topic,
                "bootstrap_servers": self.bootstrap_servers,
                "total_messages": total_messages,
                "success_count": success_count,
                "error_count": error_count,
                "send_as_batch": self.send_as_batch,
                "batch_size": self.batch_size if self.send_as_batch else 1,
                "serializer": self.value_serializer,
                "compression": self.compression_type,
            }

            if error_count == 0:
                self.status = i18n.t("components.input_output.kafka_output.status.success", success=success_count)
            else:
                self.status = i18n.t(
                    "components.input_output.kafka_output.status.partial_success",
                    success=success_count,
                    errors=error_count,
                )

            return Data(data=result_info)

        except Exception as e:
            error_msg = i18n.t("components.input_output.kafka_output.errors.send_failed", error=str(e))
            self.status = error_msg
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        finally:
            # Clean up producer
            if self._producer:
                try:
                    self._producer.flush(timeout=5)
                except Exception:
                    pass

    async def _send_batch(self, producer, batch: List[Dict[str, Any]], headers: Dict[str, str]) -> int:
        """Send a batch of messages to Kafka."""
        success_count = 0

        for data_item in batch:
            try:
                await self._send_single_message(producer, data_item, headers)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send message in batch: {e}")

        return success_count

    async def _send_single_message(self, producer, data_item: Dict[str, Any], headers: Dict[str, str]):
        """Send a single message to Kafka."""
        # Extract key
        key = self._extract_key(data_item)
        key_bytes = key.encode("utf-8") if key else None

        # Serialize value
        value_bytes = self._serialize_value(data_item)

        # Convert headers to list of tuples for confluent-kafka
        kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

        # Get partition (only pass if not None)
        partition = self._get_partition(data_item)

        # Prepare produce arguments
        produce_args = {
            "topic": self.topic,
            "key": key_bytes,
            "value": value_bytes,
            "headers": kafka_headers,
            "callback": self._delivery_report,
        }

        # Only add partition if it's not None
        if partition is not None:
            produce_args["partition"] = partition

        # Send message asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: producer.produce(**produce_args),
        )

        # Poll to handle delivery reports
        producer.poll(0)

    def _get_partition(self, data_item: Dict[str, Any]) -> Optional[int]:
        """Determine partition for message based on partition key or key field."""
        if self.partition_key and self.partition_key in data_item:
            # Simple hash-based partitioning
            partition_value = str(data_item[self.partition_key])
            return hash(partition_value) % 100  # Assume max 100 partitions
        elif self.key_field and self.key_field in data_item:
            key_value = str(data_item[self.key_field])
            return hash(key_value) % 100
        return None  # Let Kafka decide

    def test_connection(self) -> dict:
        """Test Kafka connection and provide diagnostic information."""
        try:
            self.status = i18n.t("components.input_output.kafka_output.status.testing_connection")

            # Import confluent-kafka
            try:
                from confluent_kafka import Producer
            except ImportError as import_err:
                return {
                    "success": False,
                    "error": i18n.t("components.input_output.kafka_output.errors.kafka_not_installed"),
                    "details": str(import_err),
                }

            diagnostic_info = {
                "bootstrap_servers": self.bootstrap_servers,
                "topic": self.topic,
                "sasl_enabled": bool(self.sasl_username and self.sasl_password),
                "compression_type": self.compression_type,
                "acks": self.acks,
            }

            # Test 1: Create producer
            try:
                producer = self._create_producer()
                diagnostic_info["producer_creation"] = "success"
            except Exception as e:
                diagnostic_info["producer_creation"] = "failed"
                return {
                    "success": False,
                    "error": f"Failed to create producer: {e!s}",
                    "diagnostic": diagnostic_info,
                }

            # Test 2: Get metadata
            try:
                # Try to get cluster metadata by producing a test message
                test_data = {"test": True, "timestamp": "2024-01-01T00:00:00Z"}
                test_value = self._serialize_value(test_data)

                # Produce a test message (but don't actually send to real topic)
                producer.produce(
                    topic=f"{self.topic}_test",
                    value=test_value,
                    callback=lambda err, msg: None,
                )

                # If we get here, producer configuration is likely correct
                diagnostic_info["metadata_test"] = "success"
            except Exception as e:
                diagnostic_info["metadata_test"] = "failed"
                producer.close()
                return {
                    "success": False,
                    "error": f"Failed to access Kafka cluster: {e!s}",
                    "diagnostic": diagnostic_info,
                }

            # Clean up
            producer.flush(timeout=2)
            producer.close()

            return {
                "success": True,
                "message": "Connection test successful",
                "diagnostic": diagnostic_info,
                "recommendations": self._get_connection_recommendations(diagnostic_info),
            }

        except Exception as e:
            return {"success": False, "error": f"Connection test failed: {e!s}", "diagnostic": {"error": str(e)}}

    def _get_connection_recommendations(self, diagnostic: dict) -> list[str]:
        """Get connection recommendations based on diagnostic information."""
        recommendations = []

        if diagnostic.get("producer_creation") == "failed":
            recommendations.append("Check bootstrap servers format (e.g., 'localhost:9092')")
            recommendations.append("Verify Kafka cluster is running and accessible")

        if diagnostic.get("sasl_enabled"):
            recommendations.append("Verify SASL username and password are correct")
            recommendations.append("Check if SASL authentication is properly configured on Kafka broker")

        if diagnostic.get("compression_type") != "none":
            recommendations.append("Verify compression codec is supported by Kafka broker")

        if diagnostic.get("acks") == "all":
            recommendations.append("Ensure all replicas are healthy for 'all' acknowledgment level")

        return recommendations

    def get_producer_info(self) -> Data:
        """Get Kafka producer configuration information."""
        info = {
            "bootstrap_servers": self.bootstrap_servers,
            "topic": self.topic,
            "key_field": self.key_field if self.key_field else None,
            "value_serializer": self.value_serializer,
            "partition_key": self.partition_key if self.partition_key else None,
            "compression_type": self.compression_type,
            "batch_size": self.batch_size,
            "timeout_ms": self.timeout_ms,
            "acks": self.acks,
            "retries": self.retries,
            "send_as_batch": self.send_as_batch,
            "headers_count": len(self.headers) if self.headers else 0,
            "sasl_enabled": bool(self.sasl_username and self.sasl_password),
            "producer_active": self._producer is not None,
        }
        return Data(data=info)
