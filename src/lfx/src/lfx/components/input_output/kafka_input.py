import json
from typing import Any

import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.schema import Data


class ETLKafkaInputComponent(Component):
    display_name = i18n.t("components.input_output.kafka_input.display_name")
    description = i18n.t("components.input_output.kafka_input.description")
    icon = "activity"
    name = "ETLKafkaInput"

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
            value=10000,
            advanced=True,
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
        ),
        Output(
            name="consumer_info",
            display_name=i18n.t("components.input_output.kafka_input.outputs.consumer_info.display_name"),
            method="get_consumer_info",
        ),
    ]

    def consume_messages(self) -> list[Data]:
        """Consume messages from Kafka topics with authentication support."""
        try:
            self.status = i18n.t("components.input_output.kafka_input.status.connecting")

            # Import kafka-python
            try:
                from kafka import KafkaConsumer
            except ImportError:
                raise ImportError(i18n.t("components.input_output.kafka_input.errors.kafka_not_installed"))

            # Parse topics
            topics = [t.strip() for t in self.topics.split(",")]

            # Configure consumer
            consumer_config = {
                "bootstrap_servers": self.bootstrap_servers.split(","),
                "group_id": self.group_id,
                "auto_offset_reset": "earliest",
                "enable_auto_commit": self.auto_commit,
                "consumer_timeout_ms": self.timeout_ms,
            }

            # Add SASL authentication if provided
            if self.sasl_username and self.sasl_password:
                consumer_config.update(
                    {
                        "security_protocol": "SASL_PLAINTEXT",
                        "sasl_mechanism": "PLAIN",
                        "sasl_plain_username": self.sasl_username,
                        "sasl_plain_password": self.sasl_password,
                    }
                )

            # Configure value deserializer
            if self.value_deserializer == "json":
                consumer_config["value_deserializer"] = lambda m: json.loads(m.decode("utf-8"))
            else:
                consumer_config["value_deserializer"] = lambda m: m.decode("utf-8")

            # Create consumer
            consumer = KafkaConsumer(*topics, **consumer_config)

            result_data = []
            message_count = 0

            self.status = i18n.t("components.input_output.kafka_input.status.consuming")

            for message in consumer:
                try:
                    value = message.value

                    # Extract data using JSONPath if provided
                    if self.json_path and isinstance(value, dict):
                        value = self._extract_json_path(value)

                    # Handle list or single item
                    if isinstance(value, list):
                        for item in value:
                            result_data.append(Data(data=item))
                    else:
                        message_data = {
                            "topic": message.topic,
                            "partition": message.partition,
                            "offset": message.offset,
                            "timestamp": message.timestamp,
                            "value": value,
                        }
                        result_data.append(Data(data=message_data))

                    message_count += 1

                    if message_count >= self.max_messages:
                        break

                except Exception as e:
                    self.log(f"Error processing message: {e}")
                    continue

            consumer.close()

            self.status = i18n.t("components.input_output.kafka_input.status.success", messages=len(result_data))
            return result_data

        except Exception as e:
            error_msg = i18n.t("components.input_output.kafka_input.errors.consume_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

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

    def get_consumer_info(self) -> Data:
        """Get Kafka consumer information."""
        info = {
            "bootstrap_servers": self.bootstrap_servers,
            "topics": self.topics,
            "group_id": self.group_id,
            "max_messages": self.max_messages,
        }
        return Data(data=info)
