import os
import i18n
from langchain_community.vectorstores import Cassandra

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import BoolInput, DictInput, FloatInput
from lfx.io import (
    DropdownInput,
    HandleInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class CassandraVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.cassandra.cassandra.display_name')
    description = i18n.t('components.cassandra.cassandra.description')
    documentation = "https://python.langchain.com/docs/modules/data_connection/vectorstores/integrations/cassandra"
    name = "Cassandra"
    icon = "Cassandra"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="database_ref",
            display_name=i18n.t(
                'components.cassandra.cassandra.database_ref.display_name'),
            info=i18n.t('components.cassandra.cassandra.database_ref.info'),
            required=True,
        ),
        MessageTextInput(
            name="username",
            display_name=i18n.t(
                'components.cassandra.cassandra.username.display_name'),
            info=i18n.t('components.cassandra.cassandra.username.info')
        ),
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.cassandra.cassandra.token.display_name'),
            info=i18n.t('components.cassandra.cassandra.token.info'),
            required=True,
        ),
        MessageTextInput(
            name="keyspace",
            display_name=i18n.t(
                'components.cassandra.cassandra.keyspace.display_name'),
            info=i18n.t('components.cassandra.cassandra.keyspace.info'),
            required=True,
        ),
        MessageTextInput(
            name="table_name",
            display_name=i18n.t(
                'components.cassandra.cassandra.table_name.display_name'),
            info=i18n.t('components.cassandra.cassandra.table_name.info'),
            required=True,
        ),
        IntInput(
            name="ttl_seconds",
            display_name=i18n.t(
                'components.cassandra.cassandra.ttl_seconds.display_name'),
            info=i18n.t('components.cassandra.cassandra.ttl_seconds.info'),
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t(
                'components.cassandra.cassandra.batch_size.display_name'),
            info=i18n.t('components.cassandra.cassandra.batch_size.info'),
            value=16,
            advanced=True,
        ),
        DropdownInput(
            name="setup_mode",
            display_name=i18n.t(
                'components.cassandra.cassandra.setup_mode.display_name'),
            info=i18n.t('components.cassandra.cassandra.setup_mode.info'),
            options=["Sync", "Async", "Off"],
            value="Sync",
            advanced=True,
        ),
        DictInput(
            name="cluster_kwargs",
            display_name=i18n.t(
                'components.cassandra.cassandra.cluster_kwargs.display_name'),
            info=i18n.t('components.cassandra.cassandra.cluster_kwargs.info'),
            advanced=True,
            list=True,
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.cassandra.cassandra.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.cassandra.cassandra.number_of_results.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra.number_of_results.info'),
            value=4,
            advanced=True,
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.cassandra.cassandra.search_type.display_name'),
            info=i18n.t('components.cassandra.cassandra.search_type.info'),
            options=["Similarity", "Similarity with score threshold",
                     "MMR (Max Marginal Relevance)"],
            value="Similarity",
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name=i18n.t(
                'components.cassandra.cassandra.search_score_threshold.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra.search_score_threshold.info'),
            value=0,
            advanced=True,
        ),
        DictInput(
            name="search_filter",
            display_name=i18n.t(
                'components.cassandra.cassandra.search_filter.display_name'),
            info=i18n.t('components.cassandra.cassandra.search_filter.info'),
            advanced=True,
            list=True,
        ),
        MessageTextInput(
            name="body_search",
            display_name=i18n.t(
                'components.cassandra.cassandra.body_search.display_name'),
            info=i18n.t('components.cassandra.cassandra.body_search.info'),
            advanced=True,
        ),
        BoolInput(
            name="enable_body_search",
            display_name=i18n.t(
                'components.cassandra.cassandra.enable_body_search.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra.enable_body_search.info'),
            value=False,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> Cassandra:
        try:
            import cassio
            from langchain_community.utilities.cassandra import SetupMode
            logger.debug(
                i18n.t('components.cassandra.cassandra.logs.cassio_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.cassandra.cassandra.errors.cassio_not_installed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        from uuid import UUID

        database_ref = self.database_ref

        # Detect Astra DB or regular Cassandra
        try:
            UUID(self.database_ref)
            is_astra = True
            logger.info(i18n.t('components.cassandra.cassandra.logs.detected_astra',
                               database_id=self.database_ref))
        except ValueError:
            is_astra = False
            if "," in self.database_ref:
                database_ref = self.database_ref.split(",")
                logger.info(i18n.t('components.cassandra.cassandra.logs.detected_cassandra_multiple',
                                   count=len(database_ref)))
            else:
                logger.info(i18n.t('components.cassandra.cassandra.logs.detected_cassandra_single',
                                   contact_point=self.database_ref))

        # Initialize cassio
        self.status = i18n.t(
            'components.cassandra.cassandra.status.connecting')

        try:
            if is_astra:
                logger.debug(i18n.t('components.cassandra.cassandra.logs.connecting_astra',
                                    database_id=database_ref))
                cassio.init(
                    database_id=database_ref,
                    token=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )
                logger.info(
                    i18n.t('components.cassandra.cassandra.logs.astra_connected'))
            else:
                logger.debug(i18n.t('components.cassandra.cassandra.logs.connecting_cassandra',
                                    contact_points=database_ref,
                                    username=self.username))
                cassio.init(
                    contact_points=database_ref,
                    username=self.username,
                    password=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )
                logger.info(
                    i18n.t('components.cassandra.cassandra.logs.cassandra_connected'))
        except Exception as e:
            error_msg = i18n.t('components.cassandra.cassandra.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # Prepare documents
        self.status = i18n.t(
            'components.cassandra.cassandra.status.preparing_documents')

        self.ingest_data = self._prepare_ingest_data()
        documents = []

        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        body_index_options = [("index_analyzer", "STANDARD")
                              ] if self.enable_body_search else None

        if self.enable_body_search:
            logger.debug(
                i18n.t('components.cassandra.cassandra.logs.body_search_enabled'))

        if self.setup_mode == "Off":
            setup_mode = SetupMode.OFF
        elif self.setup_mode == "Sync":
            setup_mode = SetupMode.SYNC
        else:
            setup_mode = SetupMode.ASYNC

        logger.debug(i18n.t('components.cassandra.cassandra.logs.setup_mode_set',
                            mode=self.setup_mode))

        # Build vector store
        self.status = i18n.t(
            'components.cassandra.cassandra.status.building_store')

        try:
            if documents:
                self.log(i18n.t('components.cassandra.cassandra.logs.adding_documents',
                                count=len(documents)))
                logger.info(i18n.t('components.cassandra.cassandra.logs.creating_from_documents',
                                   count=len(documents),
                                   table=self.table_name,
                                   keyspace=self.keyspace))

                table = Cassandra.from_documents(
                    documents=documents,
                    embedding=self.embedding,
                    table_name=self.table_name,
                    keyspace=self.keyspace,
                    ttl_seconds=self.ttl_seconds or None,
                    batch_size=self.batch_size,
                    body_index_options=body_index_options,
                )
            else:
                self.log(
                    i18n.t('components.cassandra.cassandra.logs.no_documents'))
                logger.info(i18n.t('components.cassandra.cassandra.logs.creating_empty_store',
                                   table=self.table_name,
                                   keyspace=self.keyspace))

                table = Cassandra(
                    embedding=self.embedding,
                    table_name=self.table_name,
                    keyspace=self.keyspace,
                    ttl_seconds=self.ttl_seconds or None,
                    body_index_options=body_index_options,
                    setup_mode=setup_mode,
                )

            success_msg = i18n.t('components.cassandra.cassandra.success.store_created',
                                 table=self.table_name)
            logger.info(success_msg)
            self.status = success_msg

            return table

        except Exception as e:
            error_msg = i18n.t('components.cassandra.cassandra.errors.store_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _map_search_type(self) -> str:
        """Map display search type to internal search type."""
        if self.search_type == "Similarity with score threshold":
            return "similarity_score_threshold"
        if self.search_type == "MMR (Max Marginal Relevance)":
            return "mmr"
        return "similarity"

    def search_documents(self) -> list[Data]:
        """Search documents in the vector store."""
        try:
            vector_store = self.build_vector_store()

            self.log(i18n.t('components.cassandra.cassandra.logs.search_input',
                            query=self.search_query))
            self.log(i18n.t('components.cassandra.cassandra.logs.search_type',
                            type=self.search_type))
            self.log(i18n.t('components.cassandra.cassandra.logs.number_of_results',
                            count=self.number_of_results))

            if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
                self.status = i18n.t(
                    'components.cassandra.cassandra.status.searching')

                try:
                    search_type = self._map_search_type()
                    search_args = self._build_search_args()

                    self.log(i18n.t('components.cassandra.cassandra.logs.search_args',
                                    args=search_args))

                    logger.debug(i18n.t('components.cassandra.cassandra.logs.executing_search',
                                        query=self.search_query,
                                        search_type=search_type))

                    docs = vector_store.search(
                        query=self.search_query, search_type=search_type, **search_args)

                except KeyError as e:
                    if "content" in str(e):
                        error_msg = i18n.t(
                            'components.cassandra.cassandra.errors.content_field_missing')
                        logger.error(error_msg)
                        raise ValueError(error_msg) from e
                    raise

                self.log(i18n.t('components.cassandra.cassandra.logs.retrieved_documents',
                                count=len(docs)))
                logger.info(i18n.t('components.cassandra.cassandra.logs.search_completed',
                                   count=len(docs)))

                data = docs_to_data(docs)
                self.status = data
                return data

            logger.warning(
                i18n.t('components.cassandra.cassandra.warnings.empty_query'))
            return []

        except Exception as e:
            error_msg = i18n.t('components.cassandra.cassandra.errors.search_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _build_search_args(self):
        """Build search arguments dictionary."""
        args = {
            "k": self.number_of_results,
            "score_threshold": self.search_score_threshold,
        }

        if self.search_filter:
            clean_filter = {k: v for k,
                            v in self.search_filter.items() if k and v}
            if len(clean_filter) > 0:
                args["filter"] = clean_filter
                logger.debug(i18n.t('components.cassandra.cassandra.logs.filter_applied',
                                    filter=clean_filter))

        if self.body_search:
            if not self.enable_body_search:
                error_msg = i18n.t(
                    'components.cassandra.cassandra.errors.body_search_not_enabled')
                logger.error(error_msg)
                raise ValueError(error_msg)
            args["body_search"] = self.body_search
            logger.debug(i18n.t('components.cassandra.cassandra.logs.body_search_applied',
                                terms=self.body_search))

        return args

    def get_retriever_kwargs(self):
        """Get retriever keyword arguments."""
        search_args = self._build_search_args()
        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_args,
        }
