import asyncio
import json
from typing import Any

import i18n

from lfx.base.datasource.manager import DataSourceManager
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
        self.datasource_manager = DataSourceManager()
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
        DropdownInput(
            name="datasource_selector",
            display_name=i18n.t("components.input_output.kafka_output.datasource_selector.display_name"),
            info=i18n.t("components.input_output.kafka_output.datasource_selector.info"),
            required=True,
            refresh_button=True,
            options=[],  # Will be loaded dynamically
            real_time_refresh=True,
            action_button={
                "label": i18n.t("base.dataSource.addDataSource"),
                "icon": "plus",
                "action": "open_datasource_dialog",
            },
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

        # Start with basic producer config
        producer_config = {
            "acks": self.acks,
            "retries": self.retries,
            "delivery.timeout.ms": self.timeout_ms,
            "batch.size": self.batch_size * 1024,  # Convert to bytes
            "linger.ms": 10,  # Wait up to 10ms for batching
            "queue.buffering.max.messages": 10000,
            "queue.buffering.max.kbytes": 102400,  # 100MB
            "socket.send.buffer.bytes": 102400,
        }

        # Get Kafka config from datasource (required)
        if not self.datasource_selector:
            raise ValueError("Datasource selector is required")

        logger.info(f"[KafkaOutput] Using datasource: {self.datasource_selector}")
        datasource_config = self._get_kafka_config_from_datasource()

        # Merge datasource config
        producer_config.update(datasource_config)

        # Validate bootstrap.servers is present
        if "bootstrap.servers" not in producer_config:
            raise ValueError("Datasource does not provide bootstrap.servers configuration")

        logger.debug("[KafkaOutput] Using Kafka config from datasource")

        # Add compression if not from datasource or override
        if self.compression_type != "none" and "compression.type" not in producer_config:
            producer_config["compression.type"] = self.compression_type

        bootstrap_servers = producer_config.get("bootstrap.servers", "unknown")
        logger.debug(f"Producer config: servers={bootstrap_servers}, topic={self.topic}")

        producer = Producer(producer_config)
        logger.info("Kafka producer created successfully")
        return producer

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value based on configured serializer."""
        if self.value_serializer == "json":
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False).encode("utf-8")
            return json.dumps({"value": value}, ensure_ascii=False).encode("utf-8")
        if isinstance(value, str):
            return value.encode("utf-8")
        return str(value).encode("utf-8")

    def _extract_key(self, data: dict[str, Any]) -> str:
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
                "datasource_id": self.datasource_selector,
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

    async def _send_batch(self, producer, batch: list[dict[str, Any]], headers: dict[str, str]) -> int:
        """Send a batch of messages to Kafka."""
        success_count = 0

        for data_item in batch:
            try:
                await self._send_single_message(producer, data_item, headers)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send message in batch: {e}")

        return success_count

    async def _send_single_message(self, producer, data_item: dict[str, Any], headers: dict[str, str]):
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

    def _get_partition(self, data_item: dict[str, Any]) -> int | None:
        """Determine partition for message based on partition key or key field."""
        if self.partition_key and self.partition_key in data_item:
            # Simple hash-based partitioning
            partition_value = str(data_item[self.partition_key])
            return hash(partition_value) % 100  # Assume max 100 partitions
        if self.key_field and self.key_field in data_item:
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

            # Get Kafka config from datasource for diagnostic info
            kafka_config = self._get_kafka_config_from_datasource() if self.datasource_selector else {}

            diagnostic_info = {
                "datasource_id": self.datasource_selector,
                "bootstrap_servers": kafka_config.get("bootstrap.servers", "unknown"),
                "topic": self.topic,
                "sasl_enabled": kafka_config.get("security.protocol") in ["SASL_PLAINTEXT", "SASL_SSL"],
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

    def update_build_config(
        self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None, action: str | None = None
    ) -> dict[str, Any]:
        """Update build config to load Kafka datasources dynamically."""
        logger.info(
            f"[KafkaOutput] update_build_config called - field_name: {field_name}, field_value: {field_value}"
        )

        # Load Kafka datasources for initial load or refresh
        if field_name is None or (field_name == "datasource_selector" and not field_value):
            logger.debug("[KafkaOutput] Loading Kafka datasources")
            try:
                datasources = self._load_kafka_datasources()

                # Build options and metadata
                options = []
                options_metadata = []

                for ds in datasources:
                    options.append(ds["id"])
                    options_metadata.append({
                        "value": ds["id"],
                        "label": ds["display_name"],
                        "id": ds["id"],
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": ds["source"],
                        "display_name": ds["display_name"],
                        "raw_data": ds.get("raw_data"),
                    })

                build_config["datasource_selector"]["options"] = options
                build_config["datasource_selector"]["options_metadata"] = options_metadata
                logger.debug(f"[KafkaOutput] Loaded {len(options)} Kafka datasources")

            except Exception as e:
                logger.error(f"[KafkaOutput] Error loading Kafka datasources: {e}")
                build_config["datasource_selector"]["options"] = []
                build_config["datasource_selector"]["options_metadata"] = []

        return build_config

    def _load_kafka_datasources(self) -> list[dict]:
        """Load Kafka datasources (both builtin and public), filtered by type='kafka'."""
        import asyncio
        import os

        import httpx

        all_datasources = []
        api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

        try:
            # 1. Load builtin Kafka datasources
            try:
                with httpx.Client(timeout=120.0) as client:
                    response = client.get(f"{api_url}/api/v1/datasources")

                    if response.status_code == 200:
                        datasources = response.json()
                        kafka_datasources = [ds for ds in datasources if ds.get("type", "").lower() == "kafka"]
                        logger.debug(f"[KafkaOutput] Found {len(kafka_datasources)} builtin Kafka datasources")

                        for ds in kafka_datasources:
                            datasource_id = self._extract_uuid_from_id(str(ds["id"]))
                            display_name = f"{ds['name']} (Kafka) [自定义]"
                            all_datasources.append({
                                "id": datasource_id,
                                "name": ds["name"],
                                "type": "kafka",
                                "source": "builtin",
                                "display_name": display_name,
                            })
            except Exception as e:
                logger.error(f"[KafkaOutput] Error loading builtin Kafka datasources: {e}")

            # 2. Load public Kafka datasources
            try:
                public_datasources = asyncio.run(self._get_public_datasources())
                if public_datasources:
                    kafka_public = [ds for ds in public_datasources if self._get_datasource_type(ds).lower() == "kafka"]
                    logger.debug(f"[KafkaOutput] Found {len(kafka_public)} public Kafka datasources")

                    for ds in kafka_public:
                        display_name = f"{ds['name']} (Kafka) [公共]"
                        all_datasources.append({
                            "id": str(ds["id"]),
                            "name": ds["name"],
                            "type": "kafka",
                            "source": "public",
                            "display_name": display_name,
                            "raw_data": ds,
                        })
            except Exception as e:
                logger.error(f"[KafkaOutput] Error loading public Kafka datasources: {e}")

            logger.info(f"[KafkaOutput] Loaded {len(all_datasources)} total Kafka datasources")
            return all_datasources

        except Exception as e:
            logger.error(f"[KafkaOutput] Error in _load_kafka_datasources: {e}")
            return []

    async def _get_public_datasources(self) -> list[dict]:
        """Get public datasources via feign API."""
        try:
            from lfx.services.deps import get_feign_service
            from lfx.services.feign.clients.data_construction import DataConstructionFeignClient

            feign_service = get_feign_service()
            client = DataConstructionFeignClient(feign_service)
            datasource_list = await client.get_datasource_list()

            logger.debug(f"[KafkaOutput] Got {len(datasource_list)} public datasources from feign API")
            return datasource_list if isinstance(datasource_list, list) else []

        except Exception as e:
            logger.error(f"[KafkaOutput] Failed to get public datasources: {e}")
            return []

    def _get_datasource_type(self, datasource: dict) -> str:
        """Extract datasource type from public datasource dict."""
        params = datasource.get("dataSourceParam", {})
        ds_type = params.get("type") if isinstance(params, dict) else None
        if not ds_type:
            ds_type = datasource.get("type") or datasource.get("dataSourceType") or datasource.get("dbType") or "mysql"
        return ds_type

    def _extract_uuid_from_id(self, datasource_id: str) -> str:
        """Extract pure UUID from datasource ID, removing any prefix."""
        if not datasource_id:
            return datasource_id

        if "_" in datasource_id:
            parts = datasource_id.split("_", 1)
            if len(parts) == 2:
                prefix, uuid_part = parts
                if "-" in uuid_part and len(uuid_part) == 36:
                    logger.debug(f"[KafkaOutput] Extracting UUID from datasource ID: {datasource_id} -> {uuid_part}")
                    return uuid_part

        return datasource_id

    def _find_datasource_info(self, datasource_id: str) -> dict | None:
        """Find datasource info from options_metadata."""
        # Get datasource info from build_config options_metadata
        # This should be populated by update_build_config
        try:
            # Access the component's build_config if available
            if hasattr(self, "_build_config") and self._build_config:
                datasource_selector_config = self._build_config.get("datasource_selector", {})
                options_metadata = datasource_selector_config.get("options_metadata", [])

                for option in options_metadata:
                    if option.get("id") == datasource_id or option.get("value") == datasource_id:
                        return option

            # Fallback: reload datasources if not in cache
            logger.debug("[KafkaOutput] Datasource info not in cache, reloading")
            all_datasources = self._load_kafka_datasources()
            for ds in all_datasources:
                if ds["id"] == datasource_id:
                    return {
                        "id": ds["id"],
                        "name": ds["name"],
                        "type": ds["type"],
                        "source": ds["source"],
                        "display_name": ds["display_name"],
                        "raw_data": ds.get("raw_data"),
                    }

            return None
        except Exception as e:
            logger.error(f"[KafkaOutput] Error finding datasource info: {e}")
            return None

    def _get_kafka_config_from_datasource(self) -> dict:
        """Get Kafka configuration from selected datasource (builtin or public)."""
        import os

        import httpx

        if not self.datasource_selector:
            return {}

        try:
            datasource_id = self._extract_uuid_from_id(self.datasource_selector)
            logger.info(f"[KafkaOutput] Fetching Kafka datasource configuration for ID: {datasource_id}")

            # Find datasource info to determine if it's public or builtin
            datasource_info = self._find_datasource_info(self.datasource_selector)

            kafka_config = {}

            # Check if it's a public datasource
            if datasource_info and datasource_info.get("source") == "public":
                logger.info(f"[KafkaOutput] Using public datasource: {datasource_info.get('name')}")
                raw_data = datasource_info.get("raw_data", {})
                params = raw_data.get("dataSourceParam", {})

                # Extract bootstrap servers from public datasource
                if params.get("host"):
                    kafka_config["bootstrap.servers"] = params["host"]

                # Extract authentication config
                if params.get("sasl_username"):
                    kafka_config["sasl.username"] = params["sasl_username"]
                if params.get("sasl_password"):
                    kafka_config["sasl.password"] = params["sasl_password"]
                if params.get("security_protocol"):
                    kafka_config["security.protocol"] = params["security_protocol"]
                # Default SASL protocol if username is provided
                elif params.get("sasl_username"):
                    kafka_config["security.protocol"] = "SASL_PLAINTEXT"
                if params.get("sasl_mechanism"):
                    kafka_config["sasl.mechanism"] = params["sasl_mechanism"]
                elif params.get("sasl_username"):
                    kafka_config["sasl.mechanism"] = "PLAIN"

                # Extract other Kafka producer configs from public datasource
                if params.get("compression_type"):
                    kafka_config["compression.type"] = params["compression_type"]
                if params.get("batch_size"):
                    kafka_config["batch.size"] = params["batch_size"]
                if params.get("linger_ms"):
                    kafka_config["linger.ms"] = params["linger_ms"]
                if params.get("acks"):
                    kafka_config["acks"] = params["acks"]

                logger.debug(f"[KafkaOutput] Built Kafka config from public datasource: {kafka_config}")
                return kafka_config

            # Builtin datasource: fetch via API
            api_url = os.getenv("LANGFLOW_API_URL", "http://localhost:7860")

            with httpx.Client(timeout=120.0) as client:
                response = client.get(f"{api_url}/api/v1/datasources/{datasource_id}")

                if response.status_code != 200:
                    logger.error(f"[KafkaOutput] Failed to get datasource, status: {response.status_code}")
                    return {}

                datasource = response.json()
                logger.info(f"[KafkaOutput] Using builtin datasource: {datasource.get('name')}")

                # Bootstrap servers
                if datasource.get("host"):
                    kafka_config["bootstrap.servers"] = datasource["host"]

                # Parse advanced_config
                advanced_config = datasource.get("advanced_config", {})
                if isinstance(advanced_config, str):
                    advanced_config = json.loads(advanced_config)

                # Map advanced_config to Kafka producer config
                if advanced_config.get("security_protocol"):
                    kafka_config["security.protocol"] = advanced_config["security_protocol"]
                if advanced_config.get("sasl_mechanism"):
                    kafka_config["sasl.mechanism"] = advanced_config["sasl_mechanism"]
                if advanced_config.get("sasl_username"):
                    kafka_config["sasl.username"] = advanced_config["sasl_username"]
                if advanced_config.get("sasl_password"):
                    kafka_config["sasl.password"] = advanced_config["sasl_password"]
                if advanced_config.get("compression_type"):
                    kafka_config["compression.type"] = advanced_config["compression_type"]
                if advanced_config.get("batch_size"):
                    kafka_config["batch.size"] = advanced_config["batch_size"]
                if advanced_config.get("linger_ms"):
                    kafka_config["linger.ms"] = advanced_config["linger_ms"]
                if advanced_config.get("acks"):
                    kafka_config["acks"] = advanced_config["acks"]

                logger.debug(f"[KafkaOutput] Built Kafka config from builtin datasource: {kafka_config}")
                return kafka_config

        except Exception as e:
            logger.error(f"[KafkaOutput] Error getting Kafka config from datasource: {e}")
            return {}

    def get_producer_info(self) -> Data:
        """Get Kafka producer configuration information."""
        info = {
            "datasource_id": self.datasource_selector,
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
            "producer_active": self._producer is not None,
        }
        return Data(data=info)
