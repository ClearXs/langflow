from typing import Any, cast
import i18n

from lfx.custom.custom_component.component import Component
from lfx.helpers.data import data_to_text
from lfx.inputs.inputs import DropdownInput, HandleInput, IntInput, MessageTextInput, MultilineInput, TabInput
from lfx.memory import aget_messages, astore_message
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame
from lfx.schema.dotdict import dotdict
from lfx.schema.message import Message
from lfx.template.field.base import Output
from lfx.utils.component_utils import set_current_fields, set_field_display
from lfx.utils.constants import MESSAGE_SENDER_AI, MESSAGE_SENDER_NAME_AI, MESSAGE_SENDER_USER


class MemoryComponent(Component):
    display_name = i18n.t('components.helpers.memory.display_name')
    description = i18n.t('components.helpers.memory.description')
    documentation: str = "https://docs.langflow.org/components-helpers#message-history"
    icon = "message-square-more"
    name = "Memory"
    default_keys = ["mode", "memory", "session_id"]
    mode_config = {
        "Store": ["message", "memory", "sender", "sender_name", "session_id"],
        "Retrieve": ["n_messages", "order", "template", "memory", "session_id"],
    }

    inputs = [
        TabInput(
            name="mode",
            display_name=i18n.t('components.helpers.memory.mode.display_name'),
            options=[i18n.t('components.helpers.memory.mode.retrieve'),
                     i18n.t('components.helpers.memory.mode.store')],
            value=i18n.t('components.helpers.memory.mode.retrieve'),
            info=i18n.t('components.helpers.memory.mode.info'),
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="message",
            display_name=i18n.t(
                'components.helpers.memory.message.display_name'),
            info=i18n.t('components.helpers.memory.message.info'),
            tool_mode=True,
            dynamic=True,
            show=False,
        ),
        HandleInput(
            name="memory",
            display_name=i18n.t(
                'components.helpers.memory.external_memory.display_name'),
            input_types=["Memory"],
            info=i18n.t('components.helpers.memory.external_memory.info'),
            advanced=True,
        ),
        DropdownInput(
            name="sender_type",
            display_name=i18n.t(
                'components.helpers.memory.sender_type.display_name'),
            options=[MESSAGE_SENDER_AI, MESSAGE_SENDER_USER,
                     i18n.t('components.helpers.memory.sender_type.machine_and_user')],
            value=i18n.t(
                'components.helpers.memory.sender_type.machine_and_user'),
            info=i18n.t('components.helpers.memory.sender_type.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="sender",
            display_name=i18n.t(
                'components.helpers.memory.sender.display_name'),
            info=i18n.t('components.helpers.memory.sender.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="sender_name",
            display_name=i18n.t(
                'components.helpers.memory.sender_name.display_name'),
            info=i18n.t('components.helpers.memory.sender_name.info'),
            advanced=True,
            show=False,
        ),
        IntInput(
            name="n_messages",
            display_name=i18n.t(
                'components.helpers.memory.n_messages.display_name'),
            value=100,
            info=i18n.t('components.helpers.memory.n_messages.info'),
            advanced=True,
            show=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t(
                'components.helpers.memory.session_id.display_name'),
            info=i18n.t('components.helpers.memory.session_id.info'),
            value="",
            advanced=True,
        ),
        DropdownInput(
            name="order",
            display_name=i18n.t(
                'components.helpers.memory.order.display_name'),
            options=[i18n.t('components.helpers.memory.order.ascending'),
                     i18n.t('components.helpers.memory.order.descending')],
            value=i18n.t('components.helpers.memory.order.ascending'),
            info=i18n.t('components.helpers.memory.order.info'),
            advanced=True,
            tool_mode=True,
            required=True,
        ),
        MultilineInput(
            name="template",
            display_name=i18n.t(
                'components.helpers.memory.template.display_name'),
            info=i18n.t('components.helpers.memory.template.info'),
            value="{sender_name}: {text}",
            advanced=True,
            show=False,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.helpers.memory.outputs.message.display_name'),
            name="messages_text",
            method="retrieve_messages_as_text",
            dynamic=True
        ),
        Output(
            display_name=i18n.t(
                'components.helpers.memory.outputs.dataframe.display_name'),
            name="dataframe",
            method="retrieve_messages_dataframe",
            dynamic=True
        ),
    ]

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Dynamically show only the relevant output based on the selected output type."""
        if field_name == "mode":
            # Start with empty outputs
            frontend_node["outputs"] = []
            if field_value in ["Store", i18n.t('components.helpers.memory.mode.store')]:
                frontend_node["outputs"] = [
                    Output(
                        display_name=i18n.t(
                            'components.helpers.memory.outputs.stored_messages.display_name'),
                        name="stored_messages",
                        method="store_message",
                        hidden=True,
                        dynamic=True,
                    )
                ]
            if field_value in ["Retrieve", i18n.t('components.helpers.memory.mode.retrieve')]:
                frontend_node["outputs"] = [
                    Output(
                        display_name=i18n.t(
                            'components.helpers.memory.outputs.messages.display_name'),
                        name="messages_text",
                        method="retrieve_messages_as_text",
                        dynamic=True
                    ),
                    Output(
                        display_name=i18n.t(
                            'components.helpers.memory.outputs.dataframe.display_name'),
                        name="dataframe",
                        method="retrieve_messages_dataframe",
                        dynamic=True
                    ),
                ]
        return frontend_node

    async def store_message(self) -> Message:
        try:
            message = Message(text=self.message) if isinstance(
                self.message, str) else self.message

            message.session_id = self.session_id or message.session_id
            message.sender = self.sender or message.sender or MESSAGE_SENDER_AI
            message.sender_name = self.sender_name or message.sender_name or MESSAGE_SENDER_NAME_AI

            stored_messages: list[Message] = []

            if self.memory:
                self.memory.session_id = message.session_id
                lc_message = message.to_lc_message()
                await self.memory.aadd_messages([lc_message])

                stored_messages = await self.memory.aget_messages() or []

                stored_messages = [Message.from_lc_message(
                    m) for m in stored_messages] if stored_messages else []

                if message.sender:
                    stored_messages = [
                        m for m in stored_messages if m.sender == message.sender]
            else:
                await astore_message(message, flow_id=self.graph.flow_id)
                stored_messages = (
                    await aget_messages(
                        session_id=message.session_id, sender_name=message.sender_name, sender=message.sender
                    )
                    or []
                )

            if not stored_messages:
                error_msg = i18n.t(
                    'components.helpers.memory.errors.no_messages_stored')
                raise ValueError(error_msg)

            stored_message = stored_messages[0]
            success_msg = i18n.t('components.helpers.memory.success.message_stored',
                                 sender=message.sender_name, session_id=message.session_id)
            self.status = success_msg
            return stored_message

        except Exception as e:
            error_msg = i18n.t(
                'components.helpers.memory.errors.store_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    async def retrieve_messages(self) -> Data:
        try:
            sender_type = self.sender_type
            sender_name = self.sender_name
            session_id = self.session_id
            n_messages = self.n_messages
            order = "DESC" if self.order in ["Descending", i18n.t(
                'components.helpers.memory.order.descending')] else "ASC"

            if sender_type in ["Machine and User", i18n.t('components.helpers.memory.sender_type.machine_and_user')]:
                sender_type = None

            if self.memory and not hasattr(self.memory, "aget_messages"):
                memory_name = type(self.memory).__name__
                err_msg = i18n.t('components.helpers.memory.errors.invalid_external_memory',
                                 memory_name=memory_name)
                raise AttributeError(err_msg)

            # Check if n_messages is None or 0
            if n_messages == 0:
                stored = []
            elif self.memory:
                # override session_id
                self.memory.session_id = session_id

                stored = await self.memory.aget_messages()
                # langchain memories are supposed to return messages in ascending order

                if n_messages:
                    stored = stored[-n_messages:]  # Get last N messages first

                if order == "DESC":
                    stored = stored[::-1]  # Then reverse if needed

                stored = [Message.from_lc_message(m) for m in stored]
                if sender_type:
                    expected_type = MESSAGE_SENDER_AI if sender_type == MESSAGE_SENDER_AI else MESSAGE_SENDER_USER
                    stored = [m for m in stored if m.type == expected_type]
            else:
                # For internal memory, we always fetch the last N messages by ordering by DESC
                stored = await aget_messages(
                    sender=sender_type,
                    sender_name=sender_name,
                    session_id=session_id,
                    limit=10000,
                    order=order,
                )
                if n_messages:
                    stored = stored[-n_messages:]  # Get last N messages

            success_msg = i18n.t('components.helpers.memory.success.messages_retrieved',
                                 count=len(stored), session_id=session_id)
            self.status = success_msg

            return cast("Data", stored)

        except Exception as e:
            error_msg = i18n.t(
                'components.helpers.memory.errors.retrieve_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    async def retrieve_messages_as_text(self) -> Message:
        try:
            stored_text = data_to_text(self.template, await self.retrieve_messages())

            success_msg = i18n.t(
                'components.helpers.memory.success.text_formatted')
            self.status = success_msg

            return Message(text=stored_text)

        except Exception as e:
            error_msg = i18n.t(
                'components.helpers.memory.errors.text_formatting_failed', error=str(e))
            self.status = error_msg
            return Message(text=error_msg)

    async def retrieve_messages_dataframe(self) -> DataFrame:
        """Convert the retrieved messages into a DataFrame.

        Returns:
            DataFrame: A DataFrame containing the message data.
        """
        try:
            messages = await self.retrieve_messages()
            dataframe = DataFrame(messages)

            success_msg = i18n.t('components.helpers.memory.success.dataframe_created',
                                 rows=len(messages))
            self.status = success_msg

            return dataframe

        except Exception as e:
            error_msg = i18n.t(
                'components.helpers.memory.errors.dataframe_creation_failed', error=str(e))
            self.status = error_msg
            return DataFrame([])

    def update_build_config(
        self,
        build_config: dotdict,
        field_value: Any,  # noqa: ARG002
        field_name: str | None = None,  # noqa: ARG002
    ) -> dotdict:
        return set_current_fields(
            build_config=build_config,
            action_fields=self.mode_config,
            selected_action=build_config["mode"]["value"],
            default_fields=self.default_keys,
            func=set_field_display,
        )
