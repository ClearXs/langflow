import os
from typing import Any

import i18n
from openai.lib.streaming import AssistantEventHandler

from lfx.base.astra_assistants.util import get_patched_openai_client
from lfx.custom.custom_component.component_with_cache import ComponentWithCache
from lfx.inputs.inputs import MultilineInput
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict
from lfx.schema.message import Message
from lfx.template.field.base import Output


class AssistantsRun(ComponentWithCache):
    display_name = i18n.t('components.datastax.run.display_name')
    description = i18n.t('components.datastax.run.description')
    icon = "AstraDB"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.client = get_patched_openai_client(self._shared_component_cache)
        self.thread_id = None
        logger.debug(i18n.t('components.datastax.run.logs.client_initialized'))

    def update_build_config(
        self,
        build_config: dotdict,
        field_value: Any,
        field_name: str | None = None,
    ) -> None:
        if field_name == "thread_id":
            if field_value is None:
                try:
                    logger.info(
                        i18n.t('components.datastax.run.logs.creating_new_thread'))
                    thread = self.client.beta.threads.create()
                    self.thread_id = thread.id
                    logger.info(i18n.t('components.datastax.run.logs.thread_created',
                                       thread_id=self.thread_id))
                except Exception as e:
                    logger.error(i18n.t('components.datastax.run.errors.thread_creation_failed',
                                        error=str(e)))
                    raise
            build_config["thread_id"] = field_value

    inputs = [
        MultilineInput(
            name="assistant_id",
            display_name=i18n.t(
                'components.datastax.run.assistant_id.display_name'),
            info=i18n.t('components.datastax.run.assistant_id.info'),
        ),
        MultilineInput(
            name="user_message",
            display_name=i18n.t(
                'components.datastax.run.user_message.display_name'),
            info=i18n.t('components.datastax.run.user_message.info'),
        ),
        MultilineInput(
            name="thread_id",
            display_name=i18n.t(
                'components.datastax.run.thread_id.display_name'),
            required=False,
            info=i18n.t('components.datastax.run.thread_id.info'),
        ),
        MultilineInput(
            name="env_set",
            display_name=i18n.t(
                'components.datastax.run.env_set.display_name'),
            info=i18n.t('components.datastax.run.env_set.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.run.outputs.assistant_response.display_name'),
            name="assistant_response",
            method="process_inputs"
        )
    ]

    def process_inputs(self) -> Message:
        """Execute an assistant run against a thread.

        Returns:
            Message: The assistant's response message.

        Raises:
            ValueError: If the run execution fails.
        """
        text = ""

        try:
            # Create or use existing thread
            if self.thread_id is None:
                logger.info(
                    i18n.t('components.datastax.run.logs.creating_thread_for_run'))
                thread = self.client.beta.threads.create()
                self.thread_id = thread.id
                logger.info(i18n.t('components.datastax.run.logs.thread_created_for_run',
                                   thread_id=self.thread_id))
            else:
                logger.info(i18n.t('components.datastax.run.logs.using_existing_thread',
                                   thread_id=self.thread_id))

            # Add user message to thread
            logger.info(i18n.t('components.datastax.run.logs.adding_user_message',
                               message_preview=self.user_message[:50] + ("..." if len(self.user_message) > 50 else "")))
            self.status = i18n.t(
                'components.datastax.run.status.adding_message')

            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=self.user_message
            )

            # Define event handler
            class EventHandler(AssistantEventHandler):
                def __init__(self) -> None:
                    super().__init__()

                def on_exception(self, exception: Exception) -> None:
                    logger.error(i18n.t('components.datastax.run.errors.stream_exception',
                                        error=str(exception)))
                    raise exception

            # Run assistant with streaming
            logger.info(i18n.t('components.datastax.run.logs.running_assistant',
                               assistant_id=self.assistant_id))
            self.status = i18n.t('components.datastax.run.status.running')

            event_handler = EventHandler()
            with self.client.beta.threads.runs.create_and_stream(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id,
                event_handler=event_handler,
            ) as stream:
                for part in stream.text_deltas:
                    text += part

            logger.info(i18n.t('components.datastax.run.logs.response_received',
                               length=len(text)))
            success_msg = i18n.t('components.datastax.run.status.completed',
                                 length=len(text))
            self.status = success_msg
            logger.info(success_msg)

            return Message(text=text)

        except Exception as e:
            error_msg = i18n.t('components.datastax.run.errors.run_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
