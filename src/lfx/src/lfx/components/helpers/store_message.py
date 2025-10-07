import i18n

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import (
    HandleInput,
    MessageTextInput,
)
from lfx.memory import aget_messages, astore_message
from lfx.schema.message import Message
from lfx.template.field.base import Output
from lfx.utils.constants import MESSAGE_SENDER_AI, MESSAGE_SENDER_NAME_AI


class MessageStoreComponent(Component):
    display_name = i18n.t('components.helpers.store_message.display_name')
    description = i18n.t('components.helpers.store_message.description')
    icon = "message-square-text"
    name = "StoreMessage"
    legacy = True
    replacement = ["helpers.Memory"]

    inputs = [
        MessageTextInput(
            name="message",
            display_name=i18n.t(
                'components.helpers.store_message.message.display_name'),
            info=i18n.t('components.helpers.store_message.message.info'),
            required=True,
            tool_mode=True
        ),
        HandleInput(
            name="memory",
            display_name=i18n.t(
                'components.helpers.store_message.memory.display_name'),
            input_types=["Memory"],
            info=i18n.t('components.helpers.store_message.memory.info'),
        ),
        MessageTextInput(
            name="sender",
            display_name=i18n.t(
                'components.helpers.store_message.sender.display_name'),
            info=i18n.t('components.helpers.store_message.sender.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="sender_name",
            display_name=i18n.t(
                'components.helpers.store_message.sender_name.display_name'),
            info=i18n.t('components.helpers.store_message.sender_name.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t(
                'components.helpers.store_message.session_id.display_name'),
            info=i18n.t('components.helpers.store_message.session_id.info'),
            value="",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.helpers.store_message.outputs.stored_messages.display_name'),
            name="stored_messages",
            method="store_message",
            hidden=True
        ),
    ]

    async def store_message(self) -> Message:
        try:
            # Validate message input
            if not self.message:
                error_message = i18n.t(
                    'components.helpers.store_message.errors.empty_message')
                self.status = error_message
                raise ValueError(error_message)

            message = Message(text=self.message) if isinstance(
                self.message, str) else self.message

            message.session_id = self.session_id or message.session_id
            message.sender = self.sender or message.sender or MESSAGE_SENDER_AI
            message.sender_name = self.sender_name or message.sender_name or MESSAGE_SENDER_NAME_AI

            stored_messages: list[Message] = []

            if self.memory:
                try:
                    self.memory.session_id = message.session_id
                    lc_message = message.to_lc_message()
                    await self.memory.aadd_messages([lc_message])

                    stored_messages = await self.memory.aget_messages() or []
                    stored_messages = [Message.from_lc_message(
                        m) for m in stored_messages] if stored_messages else []

                    if message.sender:
                        stored_messages = [
                            m for m in stored_messages if m.sender == message.sender]

                    success_message = i18n.t('components.helpers.store_message.success.external_memory_stored',
                                             sender=message.sender_name, session_id=message.session_id)

                except Exception as e:
                    error_message = i18n.t('components.helpers.store_message.errors.external_memory_failed',
                                           error=str(e))
                    raise ValueError(error_message) from e
            else:
                try:
                    await astore_message(message, flow_id=self.graph.flow_id)
                    stored_messages = (
                        await aget_messages(
                            session_id=message.session_id,
                            sender_name=message.sender_name,
                            sender=message.sender
                        )
                        or []
                    )

                    success_message = i18n.t('components.helpers.store_message.success.langflow_table_stored',
                                             sender=message.sender_name, session_id=message.session_id)

                except Exception as e:
                    error_message = i18n.t('components.helpers.store_message.errors.langflow_table_failed',
                                           error=str(e))
                    raise ValueError(error_message) from e

            if not stored_messages:
                error_message = i18n.t(
                    'components.helpers.store_message.errors.no_messages_stored')
                raise ValueError(error_message)

            stored_message = stored_messages[0]

            final_message = i18n.t('components.helpers.store_message.success.message_stored',
                                   sender=message.sender_name, session_id=message.session_id,
                                   total_messages=len(stored_messages))
            self.status = final_message

            return stored_message

        except ValueError:
            # Re-raise ValueError as is (already has i18n message)
            raise
        except Exception as e:
            error_message = i18n.t(
                'components.helpers.store_message.errors.unexpected_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e
