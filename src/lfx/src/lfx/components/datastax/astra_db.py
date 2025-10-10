import os

import i18n
from lfx.base.memory.model import LCChatMemoryComponent
from lfx.field_typing.constants import Memory
from lfx.inputs.inputs import MessageTextInput, SecretStrInput, StrInput
from lfx.log.logger import logger


class AstraDBChatMemory(LCChatMemoryComponent):
    display_name = i18n.t('components.datastax.astra_db.display_name')
    description = i18n.t('components.datastax.astra_db.description')
    name = "AstraDBChatMemory"
    icon: str = "AstraDB"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.datastax.astra_db.token.display_name'),
            info=i18n.t('components.datastax.astra_db.token.info'),
            value="ASTRA_DB_APPLICATION_TOKEN",
            required=True,
            advanced=os.getenv("ASTRA_ENHANCED", "false").lower() == "true",
        ),
        SecretStrInput(
            name="api_endpoint",
            display_name=i18n.t(
                'components.datastax.astra_db.api_endpoint.display_name'),
            info=i18n.t('components.datastax.astra_db.api_endpoint.info'),
            value="ASTRA_DB_API_ENDPOINT",
            required=True,
        ),
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.datastax.astra_db.collection_name.display_name'),
            info=i18n.t('components.datastax.astra_db.collection_name.info'),
            required=True,
        ),
        StrInput(
            name="namespace",
            display_name=i18n.t(
                'components.datastax.astra_db.namespace.display_name'),
            info=i18n.t('components.datastax.astra_db.namespace.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t(
                'components.datastax.astra_db.session_id.display_name'),
            info=i18n.t('components.datastax.astra_db.session_id.info'),
            advanced=True,
        ),
    ]

    def build_message_history(self) -> Memory:
        """Build Astra DB chat message history.

        Returns:
            Memory: Configured Astra DB chat message history instance.

        Raises:
            ImportError: If required packages are not installed.
            ValueError: If message history creation fails.
        """
        try:
            from langchain_astradb.chat_message_histories import AstraDBChatMessageHistory
            logger.debug(
                i18n.t('components.datastax.astra_db.logs.langchain_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.astra_db.errors.langchain_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            from astrapy.admin import parse_api_endpoint
            logger.debug(
                i18n.t('components.datastax.astra_db.logs.astrapy_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.astra_db.errors.astrapy_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.info(i18n.t('components.datastax.astra_db.logs.building_message_history',
                               collection=self.collection_name,
                               session_id=self.session_id))
            self.status = i18n.t(
                'components.datastax.astra_db.status.building')

            logger.debug(
                i18n.t('components.datastax.astra_db.logs.parsing_endpoint'))
            environment = parse_api_endpoint(self.api_endpoint).environment
            logger.debug(i18n.t('components.datastax.astra_db.logs.environment_detected',
                                environment=environment))

            namespace = self.namespace or None
            if namespace:
                logger.debug(i18n.t('components.datastax.astra_db.logs.using_namespace',
                                    namespace=namespace))
            else:
                logger.debug(
                    i18n.t('components.datastax.astra_db.logs.no_namespace'))

            message_history = AstraDBChatMessageHistory(
                session_id=self.session_id,
                collection_name=self.collection_name,
                token=self.token,
                api_endpoint=self.api_endpoint,
                namespace=namespace,
                environment=environment,
            )

            success_msg = i18n.t('components.datastax.astra_db.status.message_history_created',
                                 collection=self.collection_name,
                                 session_id=self.session_id)
            self.status = success_msg
            logger.info(success_msg)

            return message_history

        except ImportError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.datastax.astra_db.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
