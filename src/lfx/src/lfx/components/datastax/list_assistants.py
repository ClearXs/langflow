import os
import i18n
from lfx.base.astra_assistants.util import get_patched_openai_client
from lfx.custom.custom_component.component_with_cache import ComponentWithCache
from lfx.log.logger import logger
from lfx.schema.message import Message
from lfx.template.field.base import Output


class AssistantsListAssistants(ComponentWithCache):
    display_name = i18n.t('components.datastax.list_assistants.display_name')
    description = i18n.t('components.datastax.list_assistants.description')
    icon = "AstraDB"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    outputs = [
        Output(
            display_name=i18n.t(
                'components.datastax.list_assistants.outputs.assistants.display_name'),
            name="assistants",
            method="process_inputs"
        ),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.client = get_patched_openai_client(self._shared_component_cache)
        logger.debug(
            i18n.t('components.datastax.list_assistants.logs.client_initialized'))

    def process_inputs(self) -> Message:
        """List all assistants and return their IDs.

        Returns:
            Message: Message containing newline-separated assistant IDs.

        Raises:
            ValueError: If listing assistants fails.
        """
        try:
            logger.info(
                i18n.t('components.datastax.list_assistants.logs.listing_assistants'))
            self.status = i18n.t(
                'components.datastax.list_assistants.status.listing')

            assistants = self.client.beta.assistants.list().data
            id_list = [assistant.id for assistant in assistants]

            count = len(id_list)
            success_msg = i18n.t('components.datastax.list_assistants.status.listed',
                                 count=count)
            self.status = success_msg
            logger.info(success_msg)

            if count > 0:
                logger.debug(i18n.t('components.datastax.list_assistants.logs.assistant_ids',
                                    ids=", ".join(id_list[:5]) + ("..." if count > 5 else "")))
            else:
                logger.info(
                    i18n.t('components.datastax.list_assistants.logs.no_assistants'))

            return Message(text="\n".join(id_list))

        except Exception as e:
            error_msg = i18n.t('components.datastax.list_assistants.errors.listing_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
