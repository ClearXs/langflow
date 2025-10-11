import os
import i18n
from lfx.base.astra_assistants.util import get_patched_openai_client
from lfx.custom.custom_component.component_with_cache import ComponentWithCache
from lfx.inputs.inputs import MultilineInput, StrInput
from lfx.log.logger import logger
from lfx.schema.message import Message
from lfx.template.field.base import Output


class AssistantsGetAssistantName(ComponentWithCache):
    display_name = i18n.t('components.datastax.get_assistant.display_name')
    description = i18n.t('components.datastax.get_assistant.description')
    icon = "AstraDB"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="assistant_id",
            display_name=i18n.t(
                'components.datastax.get_assistant.assistant_id.display_name'),
            info=i18n.t('components.datastax.get_assistant.assistant_id.info'),
        ),
        MultilineInput(
            name="env_set",
            display_name=i18n.t(
                'components.datastax.get_assistant.env_set.display_name'),
            info=i18n.t('components.datastax.get_assistant.env_set.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.get_assistant.outputs.assistant_name.display_name'),
            name="assistant_name",
            method="process_inputs"
        ),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.client = get_patched_openai_client(self._shared_component_cache)
        logger.debug(
            i18n.t('components.datastax.get_assistant.logs.client_initialized'))

    def process_inputs(self) -> Message:
        """Retrieve assistant name by ID.

        Returns:
            Message: Message containing the assistant name.

        Raises:
            ValueError: If assistant retrieval fails.
        """
        try:
            logger.info(i18n.t('components.datastax.get_assistant.logs.retrieving_assistant',
                               assistant_id=self.assistant_id))
            self.status = i18n.t(
                'components.datastax.get_assistant.status.retrieving')

            assistant = self.client.beta.assistants.retrieve(
                assistant_id=self.assistant_id,
            )

            assistant_name = assistant.name
            success_msg = i18n.t('components.datastax.get_assistant.status.retrieved',
                                 assistant_id=self.assistant_id,
                                 assistant_name=assistant_name)
            self.status = success_msg
            logger.info(success_msg)

            return Message(text=assistant_name)

        except Exception as e:
            error_msg = i18n.t('components.datastax.get_assistant.errors.retrieval_failed',
                               assistant_id=self.assistant_id,
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
