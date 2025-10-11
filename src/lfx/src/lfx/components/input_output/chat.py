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

    async def message_response(self) -> Message:
        # Ensure files is a list and filter out empty/None values
        files = self.files if self.files else []
        if files and not isinstance(files, list):
            files = [files]
        # Filter out None/empty values
        files = [f for f in files if f is not None and f != ""]

        message = await Message.create(
            text=self.input_value,
            sender=self.sender,
            sender_name=self.sender_name,
            session_id=self.session_id,
            files=files,
        )
        if self.session_id and isinstance(message, Message) and self.should_store_message:
            stored_message = await self.send_message(
                message,
            )
            self.message.value = stored_message
            message = stored_message

        self.status = message
        return message
