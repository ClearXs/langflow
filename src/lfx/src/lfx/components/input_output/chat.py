from typing import Any, Callable
import i18n

from lfx.base.io.chat import ChatComponent
from lfx.helpers.data import safe_convert
from lfx.inputs.inputs import BoolInput, MessageTextInput, DropdownInput, HandleInput
from lfx.schema.message import Message
from lfx.schema.properties import Source
from lfx.template.field.base import Output
from lfx.utils.constants import (
    MESSAGE_SENDER_AI,
    MESSAGE_SENDER_NAME_AI,
    MESSAGE_SENDER_USER,
    MESSAGE_SENDER_NAME_USER,
)


class ChatComponent(ChatComponent):
    display_name = i18n.t('components.input_output.chat.display_name')
    description = i18n.t('components.input_output.chat.description')
    documentation: str = "https://docs.langflow.org/components-io#chat"
    icon = "MessageSquare"
    name = "Chat"
    minimized = True

    inputs = [
        MessageTextInput(
            name="text",
            display_name=i18n.t(
                'components.input_output.chat.text.display_name'),
            info=i18n.t('components.input_output.chat.text.info'),
            required=True,
        ),
        HandleInput(
            name="message",
            display_name=i18n.t(
                'components.input_output.chat.message.display_name'),
            info=i18n.t('components.input_output.chat.message.info'),
            input_types=["Message"],
            required=False,
            advanced=True,
        ),
        BoolInput(
            name="should_store_message",
            display_name=i18n.t(
                'components.input_output.chat.should_store_message.display_name'),
            info=i18n.t(
                'components.input_output.chat.should_store_message.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="sender",
            display_name=i18n.t(
                'components.input_output.chat.sender.display_name'),
            options=[MESSAGE_SENDER_AI, MESSAGE_SENDER_USER],
            value=MESSAGE_SENDER_USER,
            info=i18n.t('components.input_output.chat.sender.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="sender_name",
            display_name=i18n.t(
                'components.input_output.chat.sender_name.display_name'),
            info=i18n.t('components.input_output.chat.sender_name.info'),
            value=MESSAGE_SENDER_NAME_USER,
            advanced=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t(
                'components.input_output.chat.session_id.display_name'),
            info=i18n.t('components.input_output.chat.session_id.info'),
            advanced=True,
        ),
        BoolInput(
            name="use_message_input",
            display_name=i18n.t(
                'components.input_output.chat.use_message_input.display_name'),
            info=i18n.t('components.input_output.chat.use_message_input.info'),
            value=False,
            advanced=True,
        ),
        BoolInput(
            name="clean_data",
            display_name=i18n.t(
                'components.input_output.chat.clean_data.display_name'),
            info=i18n.t('components.input_output.chat.clean_data.info'),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.input_output.chat.outputs.message.display_name'),
            name="message",
            method="build_message",
        ),
        Output(
            display_name=i18n.t(
                'components.input_output.chat.outputs.text.display_name'),
            name="text",
            method="get_text",
        ),
    ]

    def update_build_config(self, build_config: dict[str, Any], field_value: Any, field_name: str | None = None) -> dict[str, Any]:
        """Update build config based on user selection."""
        if field_name == "use_message_input":
            if field_value:
                # Show message input, hide text input
                build_config["message"]["show"] = True
                build_config["text"]["show"] = False
            else:
                # Show text input, hide message input
                build_config["message"]["show"] = False
                build_config["text"]["show"] = True

        if field_name == "sender":
            # Update default sender name based on sender type
            if field_value == MESSAGE_SENDER_AI:
                build_config["sender_name"]["value"] = MESSAGE_SENDER_NAME_AI
            elif field_value == MESSAGE_SENDER_USER:
                build_config["sender_name"]["value"] = MESSAGE_SENDER_NAME_USER

        return build_config

    def _validate_inputs(self) -> None:
        """Validate the component inputs."""
        if self.use_message_input:
            if not self.message:
                error_message = i18n.t(
                    'components.input_output.chat.errors.message_required')
                self.status = error_message
                raise ValueError(error_message)
        else:
            if not self.text or not self.text.strip():
                error_message = i18n.t(
                    'components.input_output.chat.errors.text_required')
                self.status = error_message
                raise ValueError(error_message)

    def _build_source(self, id_: str | None, display_name: str | None, source: str | None) -> Source:
        """Build source information for the message."""
        source_dict = {}
        if id_:
            source_dict["id"] = id_
        if display_name:
            source_dict["display_name"] = display_name
        if source:
            # Handle different source types
            if hasattr(source, "model_name"):
                source_dict["source"] = source.model_name
            elif hasattr(source, "model"):
                source_dict["source"] = str(source.model)
            elif hasattr(source, "__class__"):
                source_dict["source"] = source.__class__.__name__
            else:
                source_dict["source"] = str(source)
        return Source(**source_dict)

    async def build_message(self) -> Message:
        """Build a message from the component inputs."""
        try:
            self._validate_inputs()

            # Determine text content
            if self.use_message_input and self.message:
                # Use existing message as base
                if isinstance(self.message, Message):
                    message = self.message
                    text = message.text
                else:
                    error_message = i18n.t(
                        'components.input_output.chat.errors.invalid_message_type')
                    self.status = error_message
                    raise ValueError(error_message)
            else:
                # Create new message from text
                text = safe_convert(self.text, clean_data=self.clean_data)
                message = Message(text=text)

            # Set message properties
            message.sender = self.sender
            message.sender_name = self.sender_name
            message.session_id = self.session_id or self._get_session_id()

            # Set flow_id if available
            if hasattr(self, "graph") and self.graph:
                message.flow_id = getattr(self.graph, "flow_id", None)

            # Get source properties
            source, icon, display_name, source_id = self.get_properties_from_source_component()
            message.properties.source = self._build_source(
                source_id, display_name, source)

            # Store message if needed
            if self.should_store_message and message.session_id:
                stored_message = await self.send_message(message)
                self.status = i18n.t(
                    'components.input_output.chat.success.message_stored')
                return stored_message
            else:
                self.status = i18n.t(
                    'components.input_output.chat.success.message_created')
                return message

        except Exception as e:
            error_message = i18n.t(
                'components.input_output.chat.errors.build_message_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_text(self) -> str:
        """Get the text content from the component."""
        try:
            self._validate_inputs()

            if self.use_message_input and self.message:
                if isinstance(self.message, Message):
                    return self.message.text
                else:
                    error_message = i18n.t(
                        'components.input_output.chat.errors.invalid_message_type')
                    raise ValueError(error_message)
            else:
                return safe_convert(self.text, clean_data=self.clean_data)

        except Exception as e:
            error_message = i18n.t(
                'components.input_output.chat.errors.get_text_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def _get_session_id(self) -> str | None:
        """Get the current session ID."""
        # Try to get session ID from various sources
        if hasattr(self, "graph") and self.graph:
            if hasattr(self.graph, "session_id"):
                return self.graph.session_id

        # Fallback to a default session ID or None
        return None

    def get_message_history(self, limit: int = 10) -> list[Message]:
        """Get message history for the current session."""
        try:
            session_id = self.session_id or self._get_session_id()
            if not session_id:
                return []

            # This would typically integrate with a message storage system
            # For now, return empty list as placeholder
            return []

        except Exception as e:
            warning_message = i18n.t(
                'components.input_output.chat.warnings.history_error', error=str(e))
            self.status = warning_message
            return []

    def clear_message_history(self) -> bool:
        """Clear message history for the current session."""
        try:
            session_id = self.session_id or self._get_session_id()
            if not session_id:
                return False

            # This would typically integrate with a message storage system
            # For now, return True as placeholder
            success_message = i18n.t(
                'components.input_output.chat.success.history_cleared')
            self.status = success_message
            return True

        except Exception as e:
            error_message = i18n.t(
                'components.input_output.chat.errors.clear_history_error', error=str(e))
            self.status = error_message
            return False
