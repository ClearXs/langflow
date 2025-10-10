import os
import i18n
from uuid import UUID

from lfx.base.memory.model import LCChatMemoryComponent
from lfx.field_typing.constants import Memory
from lfx.inputs.inputs import DictInput, MessageTextInput, SecretStrInput
from lfx.log.logger import logger


class CassandraChatMemory(LCChatMemoryComponent):
    display_name = i18n.t('components.cassandra.cassandra_chat.display_name')
    description = i18n.t('components.cassandra.cassandra_chat.description')
    name = "CassandraChatMemory"
    icon = "Cassandra"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="database_ref",
            display_name=i18n.t(
                'components.cassandra.cassandra_chat.database_ref.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_chat.database_ref.info'),
            required=True,
        ),
        MessageTextInput(
            name="username",
            display_name=i18n.t(
                'components.cassandra.cassandra_chat.username.display_name'),
            info=i18n.t('components.cassandra.cassandra_chat.username.info')
        ),
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.cassandra.cassandra_chat.token.display_name'),
            info=i18n.t('components.cassandra.cassandra_chat.token.info'),
            required=True,
        ),
        MessageTextInput(
            name="keyspace",
            display_name=i18n.t(
                'components.cassandra.cassandra_chat.keyspace.display_name'),
            info=i18n.t('components.cassandra.cassandra_chat.keyspace.info'),
            required=True,
        ),
        MessageTextInput(
            name="table_name",
            display_name=i18n.t(
                'components.cassandra.cassandra_chat.table_name.display_name'),
            info=i18n.t('components.cassandra.cassandra_chat.table_name.info'),
            required=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t(
                'components.cassandra.cassandra_chat.session_id.display_name'),
            info=i18n.t('components.cassandra.cassandra_chat.session_id.info'),
            advanced=True
        ),
        DictInput(
            name="cluster_kwargs",
            display_name=i18n.t(
                'components.cassandra.cassandra_chat.cluster_kwargs.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_chat.cluster_kwargs.info'),
            advanced=True,
            is_list=True,
        ),
    ]

    def build_message_history(self) -> Memory:
        """Build Cassandra chat message history."""
        try:
            self.status = i18n.t(
                'components.cassandra.cassandra_chat.status.initializing')

            # Import cassio
            try:
                import cassio
                logger.debug(
                    i18n.t('components.cassandra.cassandra_chat.logs.cassio_imported'))
            except ImportError as e:
                error_msg = i18n.t(
                    'components.cassandra.cassandra_chat.errors.cassio_not_installed')
                logger.error(error_msg)
                raise ImportError(error_msg) from e

            from langchain_community.chat_message_histories import CassandraChatMessageHistory

            database_ref = self.database_ref

            # Check if using Astra DB or regular Cassandra
            try:
                UUID(self.database_ref)
                is_astra = True
                logger.info(i18n.t('components.cassandra.cassandra_chat.logs.detected_astra',
                                   database_id=self.database_ref))
            except ValueError:
                is_astra = False
                if "," in self.database_ref:
                    # use a copy because we can't change the type of the parameter
                    database_ref = self.database_ref.split(",")
                    logger.info(i18n.t('components.cassandra.cassandra_chat.logs.detected_cassandra_multiple',
                                       count=len(database_ref)))
                else:
                    logger.info(i18n.t('components.cassandra.cassandra_chat.logs.detected_cassandra_single',
                                       contact_point=self.database_ref))

            # Initialize cassio
            self.status = i18n.t(
                'components.cassandra.cassandra_chat.status.connecting')

            if is_astra:
                logger.debug(i18n.t('components.cassandra.cassandra_chat.logs.connecting_astra',
                                    database_id=database_ref))
                cassio.init(
                    database_id=database_ref,
                    token=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )
                logger.info(
                    i18n.t('components.cassandra.cassandra_chat.logs.astra_connected'))
            else:
                logger.debug(i18n.t('components.cassandra.cassandra_chat.logs.connecting_cassandra',
                                    contact_points=database_ref,
                                    username=self.username))
                cassio.init(
                    contact_points=database_ref,
                    username=self.username,
                    password=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )
                logger.info(
                    i18n.t('components.cassandra.cassandra_chat.logs.cassandra_connected'))

            # Create message history
            self.status = i18n.t(
                'components.cassandra.cassandra_chat.status.creating_history')

            logger.debug(i18n.t('components.cassandra.cassandra_chat.logs.creating_history',
                                session_id=self.session_id,
                                table_name=self.table_name,
                                keyspace=self.keyspace))

            message_history = CassandraChatMessageHistory(
                session_id=self.session_id,
                table_name=self.table_name,
                keyspace=self.keyspace,
            )

            success_msg = i18n.t('components.cassandra.cassandra_chat.success.history_created',
                                 session_id=self.session_id,
                                 table_name=self.table_name)
            logger.info(success_msg)
            self.status = success_msg

            return message_history

        except ImportError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.cassandra.cassandra_chat.errors.initialization_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
