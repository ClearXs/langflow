from typing import Any, Dict, List, Optional, Union, Callable
import asyncio
import json
import threading
import time
from datetime import datetime
from queue import Queue, Empty
import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import (
    BoolInput,
    DropdownInput,
    HandleInput,
    MessageTextInput,
    MultilineInput,
    IntInput,
    FloatInput
)
from lfx.schema.data import Data
from lfx.schema.message import Message
from lfx.template.field.base import Output


class ListenComponent(Component):
    display_name = i18n.t('components.logic.listen.display_name')
    description = i18n.t('components.logic.listen.description')
    documentation: str = "https://docs.langflow.org/components-logic#listen"
    icon = "Radio"
    name = "Listen"

    inputs = [
        DropdownInput(
            name="listen_type",
            display_name=i18n.t(
                'components.logic.listen.listen_type.display_name'),
            info=i18n.t('components.logic.listen.listen_type.info'),
            options=["event", "message", "data_stream",
                     "file_change", "http_webhook", "queue"],
            value="event",
            required=True,
        ),
        MessageTextInput(
            name="source_identifier",
            display_name=i18n.t(
                'components.logic.listen.source_identifier.display_name'),
            info=i18n.t('components.logic.listen.source_identifier.info'),
            required=True,
        ),
        MultilineInput(
            name="filter_conditions",
            display_name=i18n.t(
                'components.logic.listen.filter_conditions.display_name'),
            info=i18n.t('components.logic.listen.filter_conditions.info'),
            placeholder='{\n  "type": "message",\n  "sender": "user",\n  "content_contains": "hello"\n}',
        ),
        DropdownInput(
            name="listen_mode",
            display_name=i18n.t(
                'components.logic.listen.listen_mode.display_name'),
            info=i18n.t('components.logic.listen.listen_mode.info'),
            options=["blocking", "non_blocking", "continuous", "single_shot"],
            value="blocking",
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.logic.listen.timeout.display_name'),
            info=i18n.t('components.logic.listen.timeout.info'),
            value=30,
            range_spec=(1, 3600),
            advanced=True,
        ),
        IntInput(
            name="max_messages",
            display_name=i18n.t(
                'components.logic.listen.max_messages.display_name'),
            info=i18n.t('components.logic.listen.max_messages.info'),
            value=0,
            range_spec=(0, 1000),
            advanced=True,
        ),
        FloatInput(
            name="poll_interval",
            display_name=i18n.t(
                'components.logic.listen.poll_interval.display_name'),
            info=i18n.t('components.logic.listen.poll_interval.info'),
            value=1.0,
            range_spec=(0.1, 60.0),
            advanced=True,
        ),
        BoolInput(
            name="auto_acknowledge",
            display_name=i18n.t(
                'components.logic.listen.auto_acknowledge.display_name'),
            info=i18n.t('components.logic.listen.auto_acknowledge.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_metadata",
            display_name=i18n.t(
                'components.logic.listen.include_metadata.display_name'),
            info=i18n.t('components.logic.listen.include_metadata.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="output_format",
            display_name=i18n.t(
                'components.logic.listen.output_format.display_name'),
            info=i18n.t('components.logic.listen.output_format.info'),
            options=["data", "message", "raw", "batch"],
            value="data",
            advanced=True,
        ),
        BoolInput(
            name="persistent_connection",
            display_name=i18n.t(
                'components.logic.listen.persistent_connection.display_name'),
            info=i18n.t('components.logic.listen.persistent_connection.info'),
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="authentication",
            display_name=i18n.t(
                'components.logic.listen.authentication.display_name'),
            info=i18n.t('components.logic.listen.authentication.info'),
            placeholder='{"type": "bearer", "token": "your_token"}',
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.listen.outputs.received_data.display_name'),
            name="received_data",
            method="listen_for_data",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.listen.outputs.listen_status.display_name'),
            name="listen_status",
            method="get_listen_status",
        ),
        Output(
            display_name=i18n.t(
                'components.logic.listen.outputs.connection_info.display_name'),
            name="connection_info",
            method="get_connection_info",
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._listening = False
        self._connection = None
        self._message_queue = Queue()
        self._listen_thread = None
        self._start_time = None
        self._received_count = 0

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "listen_type":
            if field_value == "http_webhook":
                build_config["authentication"]["show"] = True
                build_config["persistent_connection"]["show"] = False
            elif field_value == "file_change":
                build_config["poll_interval"]["show"] = True
                build_config["authentication"]["show"] = False
            elif field_value == "queue":
                build_config["auto_acknowledge"]["show"] = True
                build_config["persistent_connection"]["show"] = True
            else:
                build_config["authentication"]["show"] = False
                build_config["poll_interval"]["show"] = True

        if field_name == "listen_mode":
            if field_value == "continuous":
                build_config["max_messages"]["show"] = True
                build_config["timeout"]["show"] = False
            elif field_value == "single_shot":
                build_config["max_messages"]["show"] = False
                build_config["timeout"]["show"] = True
            else:
                build_config["max_messages"]["show"] = True
                build_config["timeout"]["show"] = True

        return build_config

    def _validate_inputs(self) -> None:
        """Validate component inputs."""
        if not self.source_identifier or not self.source_identifier.strip():
            error_message = i18n.t(
                'components.logic.listen.errors.empty_source_identifier')
            self.status = error_message
            raise ValueError(error_message)

        if self.timeout <= 0:
            error_message = i18n.t(
                'components.logic.listen.errors.invalid_timeout')
            self.status = error_message
            raise ValueError(error_message)

        if self.poll_interval <= 0:
            error_message = i18n.t(
                'components.logic.listen.errors.invalid_poll_interval')
            self.status = error_message
            raise ValueError(error_message)

        if self.filter_conditions:
            try:
                json.loads(self.filter_conditions)
            except json.JSONDecodeError as e:
                error_message = i18n.t('components.logic.listen.errors.invalid_filter_conditions',
                                       error=str(e))
                self.status = error_message
                raise ValueError(error_message) from e

        if self.authentication:
            try:
                json.loads(self.authentication)
            except json.JSONDecodeError as e:
                error_message = i18n.t('components.logic.listen.errors.invalid_authentication',
                                       error=str(e))
                self.status = error_message
                raise ValueError(error_message) from e

    def _parse_filter_conditions(self) -> Optional[Dict[str, Any]]:
        """Parse filter conditions from JSON."""
        if not self.filter_conditions:
            return None

        try:
            return json.loads(self.filter_conditions)
        except json.JSONDecodeError:
            return None

    def _matches_filter(self, data: Any) -> bool:
        """Check if data matches filter conditions."""
        filter_conditions = self._parse_filter_conditions()
        if not filter_conditions:
            return True

        try:
            # Simple filtering logic
            for key, expected_value in filter_conditions.items():
                if isinstance(data, dict):
                    actual_value = data.get(key)
                elif hasattr(data, key):
                    actual_value = getattr(data, key)
                else:
                    continue

                # Handle different comparison types
                if key.endswith("_contains"):
                    field_name = key[:-9]  # Remove "_contains"
                    if isinstance(data, dict):
                        text_value = str(data.get(field_name, ""))
                    else:
                        text_value = str(getattr(data, field_name, ""))

                    if expected_value not in text_value:
                        return False
                elif key.endswith("_gt"):
                    if actual_value <= expected_value:
                        return False
                elif key.endswith("_lt"):
                    if actual_value >= expected_value:
                        return False
                else:
                    if actual_value != expected_value:
                        return False

            return True

        except Exception as e:
            warning_message = i18n.t('components.logic.listen.warnings.filter_evaluation_error',
                                     error=str(e))
            self.status = warning_message
            return True  # Default to accepting data if filter fails

    def _create_connection(self) -> Any:
        """Create connection based on listen type."""
        try:
            if self.listen_type == "event":
                # Mock event listener
                return {"type": "event", "source": self.source_identifier}

            elif self.listen_type == "message":
                # Mock message listener
                return {"type": "message", "channel": self.source_identifier}

            elif self.listen_type == "data_stream":
                # Mock data stream connection
                return {"type": "data_stream", "stream": self.source_identifier}

            elif self.listen_type == "file_change":
                # Mock file watcher
                return {"type": "file_change", "path": self.source_identifier}

            elif self.listen_type == "http_webhook":
                # Mock webhook listener
                auth = json.loads(
                    self.authentication) if self.authentication else {}
                return {"type": "webhook", "endpoint": self.source_identifier, "auth": auth}

            elif self.listen_type == "queue":
                # Mock queue connection
                return {"type": "queue", "queue_name": self.source_identifier}

            else:
                error_message = i18n.t('components.logic.listen.errors.unsupported_listen_type',
                                       type=self.listen_type)
                raise ValueError(error_message)

        except Exception as e:
            error_message = i18n.t('components.logic.listen.errors.connection_creation_error',
                                   error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _listen_worker(self) -> None:
        """Background worker for continuous listening."""
        try:
            while self._listening:
                # Mock data reception
                mock_data = self._generate_mock_data()

                if self._matches_filter(mock_data):
                    self._message_queue.put(mock_data)
                    self._received_count += 1

                    if self.auto_acknowledge:
                        # Mock acknowledgment
                        pass

                    if self.listen_mode == "single_shot":
                        break

                    if self.max_messages > 0 and self._received_count >= self.max_messages:
                        break

                time.sleep(self.poll_interval)

        except Exception as e:
            error_data = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "listen_type": self.listen_type,
            }
            self._message_queue.put(error_data)

    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate mock data for demonstration."""
        return {
            "id": f"msg_{int(time.time() * 1000)}",
            "type": self.listen_type,
            "source": self.source_identifier,
            "content": f"Mock {self.listen_type} data",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "received_at": datetime.now().isoformat(),
                "listen_mode": self.listen_mode,
            }
        }

    def _start_listening(self) -> None:
        """Start the listening process."""
        if self._listening:
            return

        self._listening = True
        self._start_time = datetime.now()
        self._received_count = 0
        self._connection = self._create_connection()

        if self.listen_mode in ["continuous", "non_blocking"]:
            self._listen_thread = threading.Thread(target=self._listen_worker)
            self._listen_thread.daemon = True
            self._listen_thread.start()

        success_message = i18n.t('components.logic.listen.success.listening_started',
                                 type=self.listen_type, source=self.source_identifier)
        self.status = success_message

    def _stop_listening(self) -> None:
        """Stop the listening process."""
        if not self._listening:
            return

        self._listening = False

        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=1.0)

        if self._connection:
            # Mock connection cleanup
            self._connection = None

        success_message = i18n.t('components.logic.listen.success.listening_stopped',
                                 count=self._received_count)
        self.status = success_message

    def _format_output(self, data: Union[Any, List[Any]]) -> Any:
        """Format output based on output_format."""
        if self.output_format == "raw":
            return data

        elif self.output_format == "message":
            if isinstance(data, list):
                # Return first message for batch
                if data:
                    item = data[0]
                    text = item.get("content", str(item)) if isinstance(
                        item, dict) else str(item)
                    return Message(text=text)
                else:
                    return Message(text="No data received")
            else:
                text = data.get("content", str(data)) if isinstance(
                    data, dict) else str(data)
                return Message(text=text)

        elif self.output_format == "batch":
            if not isinstance(data, list):
                data = [data] if data is not None else []

            batch_data = {
                "items": data,
                "count": len(data),
                "batch_timestamp": datetime.now().isoformat(),
            }

            if self.include_metadata:
                batch_data["metadata"] = {
                    "listen_type": self.listen_type,
                    "source": self.source_identifier,
                    "listen_mode": self.listen_mode,
                    "total_received": self._received_count,
                }

            return Data(data=batch_data)

        else:  # data
            if isinstance(data, list):
                # Return first item as Data object
                if data:
                    item = data[0]
                    return Data(data=item)
                else:
                    return Data(data={"status": "no_data", "timestamp": datetime.now().isoformat()})
            else:
                return Data(data=data)

    def listen_for_data(self) -> Any:
        """Main method to listen for data."""
        try:
            self._validate_inputs()
            self._start_listening()

            received_data = []

            if self.listen_mode == "blocking":
                # Wait for data with timeout
                end_time = time.time() + self.timeout

                while time.time() < end_time:
                    try:
                        data = self._message_queue.get(
                            timeout=min(1.0, end_time - time.time()))
                        received_data.append(data)

                        if self.max_messages > 0 and len(received_data) >= self.max_messages:
                            break

                    except Empty:
                        continue

                if not received_data:
                    warning_message = i18n.t('components.logic.listen.warnings.no_data_received_timeout',
                                             timeout=self.timeout)
                    self.status = warning_message

            elif self.listen_mode == "non_blocking":
                # Get available data immediately
                while not self._message_queue.empty():
                    try:
                        data = self._message_queue.get_nowait()
                        received_data.append(data)

                        if self.max_messages > 0 and len(received_data) >= self.max_messages:
                            break

                    except Empty:
                        break

                if not received_data:
                    info_message = i18n.t(
                        'components.logic.listen.info.no_data_available')
                    self.status = info_message

            elif self.listen_mode == "continuous":
                # Wait indefinitely for data
                while self._listening:
                    try:
                        data = self._message_queue.get(timeout=1.0)
                        received_data.append(data)

                        if self.max_messages > 0 and len(received_data) >= self.max_messages:
                            break

                    except Empty:
                        continue

            elif self.listen_mode == "single_shot":
                # Wait for single message
                try:
                    data = self._message_queue.get(timeout=self.timeout)
                    received_data.append(data)
                except Empty:
                    warning_message = i18n.t('components.logic.listen.warnings.no_data_received_timeout',
                                             timeout=self.timeout)
                    self.status = warning_message

            self._stop_listening()

            # Format and return output
            if self.output_format == "batch" or len(received_data) > 1:
                result = self._format_output(received_data)
            elif received_data:
                result = self._format_output(received_data[0])
            else:
                result = self._format_output(None)

            success_message = i18n.t('components.logic.listen.success.data_received',
                                     count=len(received_data))
            self.status = success_message

            return result

        except Exception as e:
            self._stop_listening()
            error_message = i18n.t(
                'components.logic.listen.errors.listening_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_listen_status(self) -> Data:
        """Get current listening status."""
        try:
            status_data = {
                "is_listening": self._listening,
                "listen_type": self.listen_type,
                "listen_mode": self.listen_mode,
                "source_identifier": self.source_identifier,
                "received_count": self._received_count,
                "start_time": self._start_time.isoformat() if self._start_time else None,
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
                "connection_active": self._connection is not None,
                "queue_size": self._message_queue.qsize(),
                "timeout": self.timeout,
                "max_messages": self.max_messages,
                "poll_interval": self.poll_interval,
                "auto_acknowledge": self.auto_acknowledge,
                "persistent_connection": self.persistent_connection,
                "timestamp": datetime.now().isoformat(),
            }

            return Data(data=status_data)

        except Exception as e:
            error_message = i18n.t(
                'components.logic.listen.errors.status_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_connection_info(self) -> Data:
        """Get connection information."""
        try:
            connection_info = {
                "listen_type": self.listen_type,
                "source_identifier": self.source_identifier,
                "connection_details": self._connection,
                "authentication_configured": bool(self.authentication),
                "filter_conditions": self._parse_filter_conditions(),
                "output_format": self.output_format,
                "include_metadata": self.include_metadata,
                "created_at": datetime.now().isoformat(),
            }

            return Data(data=connection_info)

        except Exception as e:
            error_message = i18n.t(
                'components.logic.listen.errors.connection_info_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def __del__(self):
        """Cleanup when component is destroyed."""
        try:
            self._stop_listening()
        except:
            pass
