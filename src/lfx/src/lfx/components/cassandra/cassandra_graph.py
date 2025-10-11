import os
from uuid import UUID

import i18n
from langchain_community.graph_vectorstores import CassandraGraphVectorStore

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import DictInput, FloatInput
from lfx.io import (
    DropdownInput,
    HandleInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class CassandraGraphVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.cassandra.cassandra_graph.display_name')
    description = i18n.t('components.cassandra.cassandra_graph.description')
    name = "CassandraGraph"
    icon = "Cassandra"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="database_ref",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.database_ref.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.database_ref.info'),
            required=True,
        ),
        MessageTextInput(
            name="username",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.username.display_name'),
            info=i18n.t('components.cassandra.cassandra_graph.username.info')
        ),
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.token.display_name'),
            info=i18n.t('components.cassandra.cassandra_graph.token.info'),
            required=True,
        ),
        MessageTextInput(
            name="keyspace",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.keyspace.display_name'),
            info=i18n.t('components.cassandra.cassandra_graph.keyspace.info'),
            required=True,
        ),
        MessageTextInput(
            name="table_name",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.table_name.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.table_name.info'),
            required=True,
        ),
        DropdownInput(
            name="setup_mode",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.setup_mode.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.setup_mode.info'),
            options=["Sync", "Off"],
            value="Sync",
            advanced=True,
        ),
        DictInput(
            name="cluster_kwargs",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.cluster_kwargs.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.cluster_kwargs.info'),
            advanced=True,
            list=True,
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.number_of_results.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.number_of_results.info'),
            value=4,
            advanced=True,
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.search_type.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.search_type.info'),
            options=[
                "Traversal",
                "MMR traversal",
                "Similarity",
                "Similarity with score threshold",
                "MMR (Max Marginal Relevance)",
            ],
            value="Traversal",
            advanced=True,
        ),
        IntInput(
            name="depth",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.depth.display_name'),
            info=i18n.t('components.cassandra.cassandra_graph.depth.info'),
            value=1,
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.search_score_threshold.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.search_score_threshold.info'),
            value=0,
            advanced=True,
        ),
        DictInput(
            name="search_filter",
            display_name=i18n.t(
                'components.cassandra.cassandra_graph.search_filter.display_name'),
            info=i18n.t(
                'components.cassandra.cassandra_graph.search_filter.info'),
            advanced=True,
            list=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> CassandraGraphVectorStore:
        try:
            import cassio
            from langchain_community.utilities.cassandra import SetupMode
            logger.debug(
                i18n.t('components.cassandra.cassandra_graph.logs.cassio_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.cassandra.cassandra_graph.errors.cassio_not_installed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        database_ref = self.database_ref

        # Detect Astra DB or regular Cassandra
        try:
            UUID(self.database_ref)
            is_astra = True
            logger.info(i18n.t('components.cassandra.cassandra_graph.logs.detected_astra',
                               database_id=self.database_ref))
        except ValueError:
            is_astra = False
            if "," in self.database_ref:
                database_ref = self.database_ref.split(",")
                logger.info(i18n.t('components.cassandra.cassandra_graph.logs.detected_cassandra_multiple',
                                   count=len(database_ref)))
            else:
                logger.info(i18n.t('components.cassandra.cassandra_graph.logs.detected_cassandra_single',
                                   contact_point=self.database_ref))

        # Initialize cassio
        self.status = i18n.t(
            'components.cassandra.cassandra_graph.status.connecting')

        try:
            if is_astra:
                logger.debug(i18n.t('components.cassandra.cassandra_graph.logs.connecting_astra',
                                    database_id=database_ref))
                cassio.init(
                    database_id=database_ref,
                    token=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )
                logger.info(
                    i18n.t('components.cassandra.cassandra_graph.logs.astra_connected'))
            else:
                logger.debug(i18n.t('components.cassandra.cassandra_graph.logs.connecting_cassandra',
                                    contact_points=database_ref,
                                    username=self.username))
                cassio.init(
                    contact_points=database_ref,
                    username=self.username,
                    password=self.token,
                    cluster_kwargs=self.cluster_kwargs,
                )
                logger.info(
                    i18n.t('components.cassandra.cassandra_graph.logs.cassandra_connected'))
        except Exception as e:
            error_msg = i18n.t('components.cassandra.cassandra_graph.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # Prepare documents
        self.status = i18n.t(
            'components.cassandra.cassandra_graph.status.preparing_documents')

        self.ingest_data = self._prepare_ingest_data()
        documents = []

        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        setup_mode = SetupMode.OFF if self.setup_mode == "Off" else SetupMode.SYNC
        logger.debug(i18n.t('components.cassandra.cassandra_graph.logs.setup_mode_set',
                            mode=self.setup_mode))

        # Build vector store
        self.status = i18n.t(
            'components.cassandra.cassandra_graph.status.building_store')

        try:
            if documents:
                self.log(i18n.t('components.cassandra.cassandra_graph.logs.adding_documents',
                                count=len(documents)))
                logger.info(i18n.t('components.cassandra.cassandra_graph.logs.creating_from_documents',
                                   count=len(documents),
                                   table=self.table_name,
                                   keyspace=self.keyspace))

                store = CassandraGraphVectorStore.from_documents(
                    documents=documents,
                    embedding=self.embedding,
                    node_table=self.table_name,
                    keyspace=self.keyspace,
                )
            else:
                self.log(
                    i18n.t('components.cassandra.cassandra_graph.logs.no_documents'))
                logger.info(i18n.t('components.cassandra.cassandra_graph.logs.creating_empty_store',
                                   table=self.table_name,
                                   keyspace=self.keyspace))

                store = CassandraGraphVectorStore(
                    embedding=self.embedding,
                    node_table=self.table_name,
                    keyspace=self.keyspace,
                    setup_mode=setup_mode,
                )

            success_msg = i18n.t('components.cassandra.cassandra_graph.success.store_created',
                                 table=self.table_name)
            logger.info(success_msg)
            self.status = success_msg

            return store

        except Exception as e:
            error_msg = i18n.t('components.cassandra.cassandra_graph.errors.store_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _map_search_type(self) -> str:
        """Map display search type to internal search type."""
        search_type_map = {
            "Similarity": "similarity",
            "Similarity with score threshold": "similarity_score_threshold",
            "MMR (Max Marginal Relevance)": "mmr",
            "MMR traversal": "mmr_traversal",
            "Traversal": "traversal"
        }
        return search_type_map.get(self.search_type, "traversal")

    def search_documents(self) -> list[Data]:
        """Search documents in the vector store."""
        try:
            vector_store = self.build_vector_store()

            self.log(i18n.t('components.cassandra.cassandra_graph.logs.search_input',
                            query=self.search_query))
            self.log(i18n.t('components.cassandra.cassandra_graph.logs.search_type',
                            type=self.search_type))
            self.log(i18n.t('components.cassandra.cassandra_graph.logs.number_of_results',
                            count=self.number_of_results))

            if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
                self.status = i18n.t(
                    'components.cassandra.cassandra_graph.status.searching')

                try:
                    search_type = self._map_search_type()
                    search_args = self._build_search_args()

                    self.log(i18n.t('components.cassandra.cassandra_graph.logs.search_args',
                                    args=search_args))

                    logger.debug(i18n.t('components.cassandra.cassandra_graph.logs.executing_search',
                                        query=self.search_query,
                                        search_type=search_type))

                    docs = vector_store.search(
                        query=self.search_query, search_type=search_type, **search_args)

                except KeyError as e:
                    if "content" in str(e):
                        error_msg = i18n.t(
                            'components.cassandra.cassandra_graph.errors.content_field_missing')
                        logger.error(error_msg)
                        raise ValueError(error_msg) from e
                    raise

                self.log(i18n.t('components.cassandra.cassandra_graph.logs.retrieved_documents',
                                count=len(docs)))
                logger.info(i18n.t('components.cassandra.cassandra_graph.logs.search_completed',
                                   count=len(docs)))

                data = docs_to_data(docs)
                self.status = data
                return data

            logger.warning(
                i18n.t('components.cassandra.cassandra_graph.warnings.empty_query'))
            return []

        except Exception as e:
            error_msg = i18n.t('components.cassandra.cassandra_graph.errors.search_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _build_search_args(self):
        """Build search arguments dictionary."""
        args = {
            "k": self.number_of_results,
            "score_threshold": self.search_score_threshold,
            "depth": self.depth,
        }

        if self.search_filter:
            clean_filter = {k: v for k,
                            v in self.search_filter.items() if k and v}
            if len(clean_filter) > 0:
                args["filter"] = clean_filter
                logger.debug(i18n.t('components.cassandra.cassandra_graph.logs.filter_applied',
                                    filter=clean_filter))

        return args

    def get_retriever_kwargs(self):
        """Get retriever keyword arguments."""
        search_args = self._build_search_args()
        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_args,
        }
