import os
import i18n
from lfx.base.memory.model import LCChatMemoryComponent
from lfx.field_typing.constants import Memory
from lfx.inputs.inputs import DictInput, MessageTextInput, SecretStrInput
from lfx.log.logger import logger


class CassandraChatMemory(LCChatMemoryComponent):
    display_name = i18n.t('components.datastax.cassandra.display_name')
    description = i18n.t('components.datastax.cassandra.description')
    name = "CassandraChatMemory"
    icon = "Cassandra"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="database_ref",
            display_name=i18n.t(
                'components.datastax.cassandra.database_ref.display_name'),
            info=i18n.t('components.datastax.cassandra.database_ref.info'),
            required=True,
        ),
        MessageTextInput(
            name="username",
            display_name=i18n.t(
                'components.datastax.cassandra.username.display_name'),
            info=i18n.t('components.datastax.cassandra.username.info')
        ),
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.datastax.cassandra.token.display_name'),
            info=i18n.t('components.datastax.cassandra.token.info'),
            required=True,
        ),
        MessageTextInput(
            name="keyspace",
            display_name=i18n.t(
                'components.datastax.cassandra.keyspace.display_name'),
            info=i18n.t('components.datastax.cassandra.keyspace.info'),
            required=True,
        ),
        MessageTextInput(
            name="table_name",
            display_name=i18n.t(
                'components.datastax.cassandra.table_name.display_name'),
            info=i18n.t('components.datastax.cassandra.table_name.info'),
            required=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t(
                'components.datastax.cassandra.session_id.display_name'),
            info=i18n.t('components.datastax.cassandra.session_id.info'),
            advanced=True
        ),
        DictInput(
            name="cluster_kwargs",
            display_name=i18n.t(
                'components.datastax.cassandra.cluster_kwargs.display_name'),
            info=i18n.t('components.datastax.cassandra.cluster_kwargs.info'),
            advanced=True,
            is_list=True,
        ),
    ]

    def build_message_history(self) -> Memory:
        """Build Cassandra chat message history.

        Returns:
            Memory: Configured Cassandra chat message history instance.

        Raises:
            ImportError: If required packages are not installed.
            ValueError: If message history creation fails.
        """
        try:
            from langchain_community.chat_message_histories import CassandraChatMessageHistory
            logger.debug(
                i18n.t('components.datastax.cassandra.logs.langchain_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.cassandra.errors.langchain_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            import cassio
            logger.debug(
                i18n.t('components.datastax.cassandra.logs.cassio_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.cassandra.errors.cassio_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        from uuid import UUID

        database_ref = self.database_ref

        # Detect if this is an Astra DB instance or a standard Cassandra instance
        try:
            UUID(self.database_ref)
            is_astra = True
            logger.info(i18n.t('components.datastax.cassandra.logs.detected_astra_db',
                               database_id=self.database_ref))
        except ValueError:
            is_astra = False
            if "," in self.database_ref:
                # use a copy because we can't change the type of the parameter
                database_ref = self.database_ref.split(",")
                logger.info(i18n.t('components.datastax.cassandra.logs.detected_cassandra_cluster',
                                   contact_points=str(database_ref)))
            else:
                logger.info(i18n.t('components.datastax.cassandra.logs.detected_cassandra_single',
                                   contact_point=database_ref))

        try:
            logger.info(i18n.t('components.datastax.cassandra.logs.initializing',
                               is_astra=is_astra))
            self.status = i18n.t(
                'components.datastax.cassandra.status.initializing')

            if is_astra:
                logger.debug(
                    i18n.t('components.datastax.cassandra.logs.init_astra'))
                cassio.init(
                    database_id=database_ref,
                    token=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )
            else:
                logger.debug(i18n.t('components.datastax.cassandra.logs.init_cassandra',
                                    username=self.username))
                cassio.init(
                    contact_points=database_ref,
                    username=self.username,
                    password=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )

            logger.info(i18n.t('components.datastax.cassandra.logs.creating_message_history',
                               table=self.table_name,
                               keyspace=self.keyspace,
                               session_id=self.session_id))

            message_history = CassandraChatMessageHistory(
                session_id=self.session_id,
                table_name=self.table_name,
                keyspace=self.keyspace,
            )

            success_msg = i18n.t('components.datastax.cassandra.status.message_history_created',
                                 table=self.table_name,
                                 keyspace=self.keyspace,
                                 session_id=self.session_id)
            self.status = success_msg
            logger.info(success_msg)

            return message_history

        except ImportError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.datastax.cassandra.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
