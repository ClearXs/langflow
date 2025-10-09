import os

import i18n
import orjson

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import (
    BoolInput,
    DictInput,
    DropdownInput,
    FloatInput,
    HandleInput,
    IntInput,
    SecretStrInput,
    StrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class AstraDBGraphVectorStoreComponent(LCVectorStoreComponent):
    display_name: str = i18n.t(
        'components.datastax.astradb_graph.display_name')
    description: str = i18n.t('components.datastax.astradb_graph.description')
    name = "AstraDBGraph"
    icon: str = "AstraDB"

    inputs = [
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.datastax.astradb_graph.token.display_name'),
            info=i18n.t('components.datastax.astradb_graph.token.info'),
            value="ASTRA_DB_APPLICATION_TOKEN",
            required=True,
            advanced=os.getenv("ASTRA_ENHANCED", "false").lower() == "true",
        ),
        SecretStrInput(
            name="api_endpoint",
            display_name=i18n.t('components.datastax.astradb_graph.api_endpoint.display_name_enhanced'
                                if os.getenv("ASTRA_ENHANCED", "false").lower() == "true"
                                else 'components.datastax.astradb_graph.api_endpoint.display_name'),
            info=i18n.t('components.datastax.astradb_graph.api_endpoint.info'),
            value="ASTRA_DB_API_ENDPOINT",
            required=True,
        ),
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.datastax.astradb_graph.collection_name.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.collection_name.info'),
            required=True,
        ),
        StrInput(
            name="metadata_incoming_links_key",
            display_name=i18n.t(
                'components.datastax.astradb_graph.metadata_incoming_links_key.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.metadata_incoming_links_key.info'),
            advanced=True,
        ),
        *LCVectorStoreComponent.inputs,
        StrInput(
            name="keyspace",
            display_name=i18n.t(
                'components.datastax.astradb_graph.keyspace.display_name'),
            info=i18n.t('components.datastax.astradb_graph.keyspace.info'),
            advanced=True,
        ),
        HandleInput(
            name="embedding_model",
            display_name=i18n.t(
                'components.datastax.astradb_graph.embedding_model.display_name'),
            input_types=["Embeddings"],
            info=i18n.t(
                'components.datastax.astradb_graph.embedding_model.info'),
        ),
        DropdownInput(
            name="metric",
            display_name=i18n.t(
                'components.datastax.astradb_graph.metric.display_name'),
            info=i18n.t('components.datastax.astradb_graph.metric.info'),
            options=["cosine", "dot_product", "euclidean"],
            value="cosine",
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t(
                'components.datastax.astradb_graph.batch_size.display_name'),
            info=i18n.t('components.datastax.astradb_graph.batch_size.info'),
            advanced=True,
        ),
        IntInput(
            name="bulk_insert_batch_concurrency",
            display_name=i18n.t(
                'components.datastax.astradb_graph.bulk_insert_batch_concurrency.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.bulk_insert_batch_concurrency.info'),
            advanced=True,
        ),
        IntInput(
            name="bulk_insert_overwrite_concurrency",
            display_name=i18n.t(
                'components.datastax.astradb_graph.bulk_insert_overwrite_concurrency.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.bulk_insert_overwrite_concurrency.info'),
            advanced=True,
        ),
        IntInput(
            name="bulk_delete_concurrency",
            display_name=i18n.t(
                'components.datastax.astradb_graph.bulk_delete_concurrency.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.bulk_delete_concurrency.info'),
            advanced=True,
        ),
        DropdownInput(
            name="setup_mode",
            display_name=i18n.t(
                'components.datastax.astradb_graph.setup_mode.display_name'),
            info=i18n.t('components.datastax.astradb_graph.setup_mode.info'),
            options=["Sync", "Off"],
            advanced=True,
            value="Sync",
        ),
        BoolInput(
            name="pre_delete_collection",
            display_name=i18n.t(
                'components.datastax.astradb_graph.pre_delete_collection.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.pre_delete_collection.info'),
            advanced=True,
            value=False,
        ),
        StrInput(
            name="metadata_indexing_include",
            display_name=i18n.t(
                'components.datastax.astradb_graph.metadata_indexing_include.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.metadata_indexing_include.info'),
            advanced=True,
            list=True,
        ),
        StrInput(
            name="metadata_indexing_exclude",
            display_name=i18n.t(
                'components.datastax.astradb_graph.metadata_indexing_exclude.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.metadata_indexing_exclude.info'),
            advanced=True,
            list=True,
        ),
        StrInput(
            name="collection_indexing_policy",
            display_name=i18n.t(
                'components.datastax.astradb_graph.collection_indexing_policy.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.collection_indexing_policy.info'),
            advanced=True,
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.datastax.astradb_graph.number_of_results.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.number_of_results.info'),
            advanced=True,
            value=4,
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.datastax.astradb_graph.search_type.display_name'),
            info=i18n.t('components.datastax.astradb_graph.search_type.info'),
            options=[
                "Similarity",
                "Similarity with score threshold",
                "MMR (Max Marginal Relevance)",
                "Graph Traversal",
                "MMR (Max Marginal Relevance) Graph Traversal",
            ],
            value="MMR (Max Marginal Relevance) Graph Traversal",
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name=i18n.t(
                'components.datastax.astradb_graph.search_score_threshold.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.search_score_threshold.info'),
            value=0,
            advanced=True,
        ),
        DictInput(
            name="search_filter",
            display_name=i18n.t(
                'components.datastax.astradb_graph.search_filter.display_name'),
            info=i18n.t(
                'components.datastax.astradb_graph.search_filter.info'),
            advanced=True,
            is_list=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self):
        try:
            from langchain_astradb import AstraDBGraphVectorStore
            from langchain_astradb.utils.astradb import SetupMode
            logger.debug(
                i18n.t('components.datastax.astradb_graph.logs.langchain_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.astradb_graph.errors.langchain_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            if not self.setup_mode:
                self.setup_mode = self._inputs["setup_mode"].options[0]

            setup_mode_value = SetupMode[self.setup_mode.upper()]
            logger.debug(i18n.t('components.datastax.astradb_graph.logs.setup_mode_set',
                                mode=self.setup_mode))
        except KeyError as e:
            error_msg = i18n.t('components.datastax.astradb_graph.errors.invalid_setup_mode',
                               mode=self.setup_mode)
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        try:
            logger.info(i18n.t('components.datastax.astradb_graph.logs.initializing',
                               collection=self.collection_name))

            # Handle environment parsing with try-except to avoid circular import
            environment = None
            if self.api_endpoint:
                try:
                    from astrapy.admin import parse_api_endpoint

                    environment = parse_api_endpoint(
                        self.api_endpoint).environment
                    logger.debug(i18n.t('components.datastax.astradb_graph.logs.environment_detected',
                                        environment=environment))
                except ImportError:
                    logger.warning(
                        i18n.t('components.datastax.astradb_graph.logs.environment_parse_warning'))
                    environment = None

            vector_store = AstraDBGraphVectorStore(
                embedding=self.embedding_model,
                collection_name=self.collection_name,
                metadata_incoming_links_key=self.metadata_incoming_links_key or "incoming_links",
                token=self.token,
                api_endpoint=self.api_endpoint,
                namespace=self.keyspace or None,
                environment=environment,
                metric=self.metric or None,
                batch_size=self.batch_size or None,
                bulk_insert_batch_concurrency=self.bulk_insert_batch_concurrency or None,
                bulk_insert_overwrite_concurrency=self.bulk_insert_overwrite_concurrency or None,
                bulk_delete_concurrency=self.bulk_delete_concurrency or None,
                setup_mode=setup_mode_value,
                pre_delete_collection=self.pre_delete_collection,
                metadata_indexing_include=[
                    s for s in self.metadata_indexing_include if s] or None,
                metadata_indexing_exclude=[
                    s for s in self.metadata_indexing_exclude if s] or None,
                collection_indexing_policy=orjson.loads(
                    self.collection_indexing_policy.encode("utf-8"))
                if self.collection_indexing_policy
                else None,
            )
        except Exception as e:
            error_msg = i18n.t('components.datastax.astradb_graph.errors.initialization_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        logger.info(i18n.t('components.datastax.astradb_graph.logs.initialized',
                           collection=vector_store.astra_env.collection_name))
        self._add_documents_to_vector_store(vector_store)

        return vector_store

    def _add_documents_to_vector_store(self, vector_store) -> None:
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                error_msg = i18n.t(
                    'components.datastax.astradb_graph.errors.invalid_input_type')
                logger.error(error_msg)
                raise TypeError(error_msg)

        if documents:
            logger.info(i18n.t('components.datastax.astradb_graph.logs.adding_documents',
                               count=len(documents)))
            try:
                vector_store.add_documents(documents)
                logger.info(i18n.t('components.datastax.astradb_graph.logs.documents_added',
                                   count=len(documents)))
            except Exception as e:
                error_msg = i18n.t('components.datastax.astradb_graph.errors.add_documents_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e
        else:
            logger.info(
                i18n.t('components.datastax.astradb_graph.logs.no_documents'))

    def _map_search_type(self) -> str:
        logger.debug(i18n.t('components.datastax.astradb_graph.logs.mapping_search_type',
                            search_type=self.search_type))

        match self.search_type:
            case "Similarity":
                return "similarity"
            case "Similarity with score threshold":
                return "similarity_score_threshold"
            case "MMR (Max Marginal Relevance)":
                return "mmr"
            case "Graph Traversal":
                return "traversal"
            case "MMR (Max Marginal Relevance) Graph Traversal":
                return "mmr_traversal"
            case _:
                return "similarity"

    def _build_search_args(self):
        args = {
            "k": self.number_of_results,
            "score_threshold": self.search_score_threshold,
        }

        if self.search_filter:
            clean_filter = {k: v for k,
                            v in self.search_filter.items() if k and v}
            if len(clean_filter) > 0:
                args["filter"] = clean_filter
                logger.debug(i18n.t('components.datastax.astradb_graph.logs.filter_applied',
                                    count=len(clean_filter)))

        return args

    def search_documents(self, vector_store=None) -> list[Data]:
        if not vector_store:
            vector_store = self.build_vector_store()

        logger.info(i18n.t('components.datastax.astradb_graph.logs.searching'))
        logger.info(i18n.t('components.datastax.astradb_graph.logs.search_query',
                           query=self.search_query))
        logger.info(i18n.t('components.datastax.astradb_graph.logs.search_type_log',
                           search_type=self.search_type))
        logger.info(i18n.t('components.datastax.astradb_graph.logs.number_of_results',
                           count=self.number_of_results))

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            try:
                search_type = self._map_search_type()
                search_args = self._build_search_args()

                docs = vector_store.search(
                    query=self.search_query, search_type=search_type, **search_args)

                # Drop links from the metadata
                logger.debug(
                    i18n.t('components.datastax.astradb_graph.logs.removing_links'))
                for doc in docs:
                    if "links" in doc.metadata:
                        doc.metadata.pop("links")

            except Exception as e:
                error_msg = i18n.t('components.datastax.astradb_graph.errors.search_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

            logger.info(i18n.t('components.datastax.astradb_graph.logs.retrieved_documents',
                               count=len(docs)))

            data = docs_to_data(docs)

            logger.info(i18n.t('components.datastax.astradb_graph.logs.converted_to_data',
                               count=len(data)))

            self.status = data
            return data

        logger.info(
            i18n.t('components.datastax.astradb_graph.logs.no_search_input'))
        return []

    def get_retriever_kwargs(self):
        search_args = self._build_search_args()
        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_args,
        }
