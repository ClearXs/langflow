import os
import i18n
from lfx.base.astra_assistants.util import get_patched_openai_client
from lfx.custom.custom_component.component_with_cache import ComponentWithCache
from lfx.inputs.inputs import MultilineInput
from lfx.log.logger import logger
from lfx.schema.message import Message
from lfx.template.field.base import Output


class AssistantsCreateThread(ComponentWithCache):
    display_name = i18n.t('components.datastax.create_thread.display_name')
    description = i18n.t('components.datastax.create_thread.description')
    icon = "AstraDB"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MultilineInput(
            name="env_set",
            display_name=i18n.t(
                'components.datastax.create_thread.env_set.display_name'),
            info=i18n.t('components.datastax.create_thread.env_set.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.create_thread.outputs.thread_id.display_name'),
            name="thread_id",
            method="process_inputs"
        ),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.client = get_patched_openai_client(self._shared_component_cache)
        logger.debug(
            i18n.t('components.datastax.create_thread.logs.client_initialized'))

    def process_inputs(self) -> Message:
        """Create a thread and return its ID.

        Returns:
            Message: Message containing the thread ID.

        Raises:
            ValueError: If thread creation fails.
        """
        try:
            logger.info(i18n.t('components.datastax.create_thread.logs.processing_inputs',
                               env_set=self.env_set))

            logger.info(
                i18n.t('components.datastax.create_thread.logs.creating_thread'))
            self.status = i18n.t(
                'components.datastax.create_thread.status.creating')

            thread = self.client.beta.threads.create()
            thread_id = thread.id

            success_msg = i18n.t('components.datastax.create_thread.status.created',
                                 thread_id=thread_id)
            self.status = success_msg
            logger.info(success_msg)

            return Message(text=thread_id)

        except Exception as e:
            error_msg = i18n.t('components.datastax.create_thread.errors.creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
