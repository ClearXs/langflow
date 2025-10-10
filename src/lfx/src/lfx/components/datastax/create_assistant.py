import os
import i18n
from lfx.base.astra_assistants.util import get_patched_openai_client
from lfx.custom.custom_component.component_with_cache import ComponentWithCache
from lfx.inputs.inputs import MultilineInput, StrInput
from lfx.log.logger import logger
from lfx.schema.message import Message
from lfx.template.field.base import Output


class AssistantsCreateAssistant(ComponentWithCache):
    icon = "AstraDB"
    display_name = i18n.t('components.datastax.create_assistant.display_name')
    description = i18n.t('components.datastax.create_assistant.description')

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="assistant_name",
            display_name=i18n.t(
                'components.datastax.create_assistant.assistant_name.display_name'),
            info=i18n.t(
                'components.datastax.create_assistant.assistant_name.info'),
        ),
        StrInput(
            name="instructions",
            display_name=i18n.t(
                'components.datastax.create_assistant.instructions.display_name'),
            info=i18n.t(
                'components.datastax.create_assistant.instructions.info'),
        ),
        StrInput(
            name="model",
            display_name=i18n.t(
                'components.datastax.create_assistant.model.display_name'),
            info=i18n.t('components.datastax.create_assistant.model.info'),
            # refresh_model=True
        ),
        MultilineInput(
            name="env_set",
            display_name=i18n.t(
                'components.datastax.create_assistant.env_set.display_name'),
            info=i18n.t('components.datastax.create_assistant.env_set.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.create_assistant.outputs.assistant_id.display_name'),
            name="assistant_id",
            method="process_inputs"
        ),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.client = get_patched_openai_client(self._shared_component_cache)
        logger.debug(
            i18n.t('components.datastax.create_assistant.logs.client_initialized'))

    def process_inputs(self) -> Message:
        """Create an assistant and return its ID.

        Returns:
            Message: Message containing the assistant ID.

        Raises:
            ValueError: If assistant creation fails.
        """
        try:
            logger.info(i18n.t('components.datastax.create_assistant.logs.processing_inputs',
                               env_set=self.env_set))

            logger.info(i18n.t('components.datastax.create_assistant.logs.creating_assistant',
                               name=self.assistant_name,
                               model=self.model))
            self.status = i18n.t(
                'components.datastax.create_assistant.status.creating')

            assistant = self.client.beta.assistants.create(
                name=self.assistant_name,
                instructions=self.instructions,
                model=self.model,
            )

            success_msg = i18n.t('components.datastax.create_assistant.status.created',
                                 name=self.assistant_name,
                                 assistant_id=assistant.id)
            self.status = success_msg
            logger.info(success_msg)

            return Message(text=assistant.id)

        except Exception as e:
            error_msg = i18n.t('components.datastax.create_assistant.errors.creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
