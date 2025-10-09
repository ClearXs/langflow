import i18n
from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import DictInput, FloatInput
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    IntInput,
    MultilineInput,
    SecretStrInput,
    StrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class HCDVectorStoreComponent(LCVectorStoreComponent):
    display_name: str = i18n.t('components.datastax.hcd.display_name')
    description: str = i18n.t('components.datastax.hcd.description')
    name = "HCD"
    icon: str = "HCD"

    inputs = [
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.datastax.hcd.collection_name.display_name'),
            info=i18n.t('components.datastax.hcd.collection_name.info'),
            required=True,
        ),
        StrInput(
            name="username",
            display_name=i18n.t(
                'components.datastax.hcd.username.display_name'),
            info=i18n.t('components.datastax.hcd.username.info'),
            value="hcd-superuser",
            required=True,
        ),
        SecretStrInput(
            name="password",
            display_name=i18n.t(
                'components.datastax.hcd.password.display_name'),
            info=i18n.t('components.datastax.hcd.password.info'),
            value="HCD_PASSWORD",
            required=True,
        ),
        SecretStrInput(
            name="api_endpoint",
            display_name=i18n.t(
                'components.datastax.hcd.api_endpoint.display_name'),
            info=i18n.t('components.datastax.hcd.api_endpoint.info'),
            value="HCD_API_ENDPOINT",
            required=True,
        ),
        *LCVectorStoreComponent.inputs,
        StrInput(
            name="namespace",
            display_name=i18n.t(
                'components.datastax.hcd.namespace.display_name'),
            info=i18n.t('components.datastax.hcd.namespace.info'),
            value="default_namespace",
            advanced=True,
        ),
        MultilineInput(
            name="ca_certificate",
            display_name=i18n.t(
                'components.datastax.hcd.ca_certificate.display_name'),
            info=i18n.t('components.datastax.hcd.ca_certificate.info'),
            advanced=True,
        ),
        DropdownInput(
            name="metric",
            display_name=i18n.t('components.datastax.hcd.metric.display_name'),
            info=i18n.t('components.datastax.hcd.metric.info'),
            options=["cosine", "dot_product", "euclidean"],
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name=i18n.t(
                'components.datastax.hcd.batch_size.display_name'),
            info=i18n.t('components.datastax.hcd.batch_size.info'),
            advanced=True,
        ),
        IntInput(
            name="bulk_insert_batch_concurrency",
            display_name=i18n.t(
                'components.datastax.hcd.bulk_insert_batch_concurrency.display_name'),
            info=i18n.t(
                'components.datastax.hcd.bulk_insert_batch_concurrency.info'),
            advanced=True,
        ),
        IntInput(
            name="bulk_insert_overwrite_concurrency",
            display_name=i18n.t(
                'components.datastax.hcd.bulk_insert_overwrite_concurrency.display_name'),
            info=i18n.t(
                'components.datastax.hcd.bulk_insert_overwrite_concurrency.info'),
            advanced=True,
        ),
        IntInput(
            name="bulk_delete_concurrency",
            display_name=i18n.t(
                'components.datastax.hcd.bulk_delete_concurrency.display_name'),
            info=i18n.t(
                'components.datastax.hcd.bulk_delete_concurrency.info'),
            advanced=True,
        ),
        DropdownInput(
            name="setup_mode",
            display_name=i18n.t(
                'components.datastax.hcd.setup_mode.display_name'),
            info=i18n.t('components.datastax.hcd.setup_mode.info'),
            options=["Sync", "Async", "Off"],
            advanced=True,
            value="Sync",
        ),
        BoolInput(
            name="pre_delete_collection",
            display_name=i18n.t(
                'components.datastax.hcd.pre_delete_collection.display_name'),
            info=i18n.t('components.datastax.hcd.pre_delete_collection.info'),
            advanced=True,
        ),
        StrInput(
            name="metadata_indexing_include",
            display_name=i18n.t(
                'components.datastax.hcd.metadata_indexing_include.display_name'),
            info=i18n.t(
                'components.datastax.hcd.metadata_indexing_include.info'),
            advanced=True,
        ),
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.datastax.hcd.embedding.display_name'),
            input_types=["Embeddings", "dict"],
            info=i18n.t('components.datastax.hcd.embedding.info'),
        ),
        StrInput(
            name="metadata_indexing_exclude",
            display_name=i18n.t(
                'components.datastax.hcd.metadata_indexing_exclude.display_name'),
            info=i18n.t(
                'components.datastax.hcd.metadata_indexing_exclude.info'),
            advanced=True,
        ),
        StrInput(
            name="collection_indexing_policy",
            display_name=i18n.t(
                'components.datastax.hcd.collection_indexing_policy.display_name'),
            info=i18n.t(
                'components.datastax.hcd.collection_indexing_policy.info'),
            advanced=True,
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.datastax.hcd.number_of_results.display_name'),
            info=i18n.t('components.datastax.hcd.number_of_results.info'),
            advanced=True,
            value=4,
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.datastax.hcd.search_type.display_name'),
            info=i18n.t('components.datastax.hcd.search_type.info'),
            options=["Similarity", "Similarity with score threshold",
                     "MMR (Max Marginal Relevance)"],
            value="Similarity",
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name=i18n.t(
                'components.datastax.hcd.search_score_threshold.display_name'),
            info=i18n.t('components.datastax.hcd.search_score_threshold.info'),
            value=0,
            advanced=True,
        ),
        DictInput(
            name="search_filter",
            display_name=i18n.t(
                'components.datastax.hcd.search_filter.display_name'),
            info=i18n.t('components.datastax.hcd.search_filter.info'),
            advanced=True,
            is_list=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self):
        try:
            from langchain_astradb import AstraDBVectorStore
            from langchain_astradb.utils.astradb import SetupMode
            logger.debug(
                i18n.t('components.datastax.hcd.logs.langchain_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.hcd.errors.langchain_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            from astrapy.authentication import UsernamePasswordTokenProvider
            from astrapy.constants import Environment
            logger.debug(
                i18n.t('components.datastax.hcd.logs.astrapy_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.hcd.errors.astrapy_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            if not self.setup_mode:
                self.setup_mode = self._inputs["setup_mode"].options[0]

            setup_mode_value = SetupMode[self.setup_mode.upper()]
            logger.debug(i18n.t('components.datastax.hcd.logs.setup_mode_set',
                                mode=self.setup_mode))
        except KeyError as e:
            error_msg = i18n.t('components.datastax.hcd.errors.invalid_setup_mode',
                               mode=self.setup_mode)
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        if not isinstance(self.embedding, dict):
            embedding_dict = {"embedding": self.embedding}
            logger.debug(
                i18n.t('components.datastax.hcd.logs.using_embedding_model'))
        else:
            from astrapy.info import VectorServiceOptions

            dict_options = self.embedding.get(
                "collection_vector_service_options", {})
            dict_options["authentication"] = {
                k: v for k, v in dict_options.get("authentication", {}).items() if k and v
            }
            dict_options["parameters"] = {k: v for k, v in dict_options.get(
                "parameters", {}).items() if k and v}
            embedding_dict = {
                "collection_vector_service_options": VectorServiceOptions.from_dict(dict_options)}
            collection_embedding_api_key = self.embedding.get(
                "collection_embedding_api_key")
            if collection_embedding_api_key:
                embedding_dict["collection_embedding_api_key"] = collection_embedding_api_key
            logger.debug(
                i18n.t('components.datastax.hcd.logs.using_vectorize_config'))

        logger.info(i18n.t('components.datastax.hcd.logs.creating_token_provider',
                           username=self.username))
        token_provider = UsernamePasswordTokenProvider(
            self.username, self.password)

        vector_store_kwargs = {
            **embedding_dict,
            "collection_name": self.collection_name,
            "token": token_provider,
            "api_endpoint": self.api_endpoint,
            "namespace": self.namespace,
            "metric": self.metric or None,
            "batch_size": self.batch_size or None,
            "bulk_insert_batch_concurrency": self.bulk_insert_batch_concurrency or None,
            "bulk_insert_overwrite_concurrency": self.bulk_insert_overwrite_concurrency or None,
            "bulk_delete_concurrency": self.bulk_delete_concurrency or None,
            "setup_mode": setup_mode_value,
            "pre_delete_collection": self.pre_delete_collection or False,
            "environment": Environment.HCD,
        }

        if self.metadata_indexing_include:
            vector_store_kwargs["metadata_indexing_include"] = self.metadata_indexing_include
            logger.debug(
                i18n.t('components.datastax.hcd.logs.metadata_include_set'))
        elif self.metadata_indexing_exclude:
            vector_store_kwargs["metadata_indexing_exclude"] = self.metadata_indexing_exclude
            logger.debug(
                i18n.t('components.datastax.hcd.logs.metadata_exclude_set'))
        elif self.collection_indexing_policy:
            vector_store_kwargs["collection_indexing_policy"] = self.collection_indexing_policy
            logger.debug(
                i18n.t('components.datastax.hcd.logs.indexing_policy_set'))

        try:
            logger.info(i18n.t('components.datastax.hcd.logs.initializing_vector_store',
                               collection=self.collection_name,
                               namespace=self.namespace))
            vector_store = AstraDBVectorStore(**vector_store_kwargs)
            logger.info(
                i18n.t('components.datastax.hcd.logs.vector_store_initialized'))
        except Exception as e:
            error_msg = i18n.t('components.datastax.hcd.errors.initialization_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

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
                    'components.datastax.hcd.errors.invalid_input_type')
                logger.error(error_msg)
                raise TypeError(error_msg)

        if documents:
            logger.info(i18n.t('components.datastax.hcd.logs.adding_documents',
                               count=len(documents)))
            try:
                vector_store.add_documents(documents)
                logger.info(i18n.t('components.datastax.hcd.logs.documents_added',
                                   count=len(documents)))
            except Exception as e:
                error_msg = i18n.t('components.datastax.hcd.errors.add_documents_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e
        else:
            logger.info(i18n.t('components.datastax.hcd.logs.no_documents'))

    def _map_search_type(self) -> str:
        logger.debug(i18n.t('components.datastax.hcd.logs.mapping_search_type',
                            search_type=self.search_type))
        if self.search_type == "Similarity with score threshold":
            return "similarity_score_threshold"
        if self.search_type == "MMR (Max Marginal Relevance)":
            return "mmr"
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
                logger.debug(i18n.t('components.datastax.hcd.logs.filter_applied',
                                    count=len(clean_filter)))
        return args

    def search_documents(self) -> list[Data]:
        vector_store = self.build_vector_store()

        logger.info(i18n.t('components.datastax.hcd.logs.search_query',
                           query=self.search_query))
        logger.info(i18n.t('components.datastax.hcd.logs.search_type_log',
                           search_type=self.search_type))
        logger.info(i18n.t('components.datastax.hcd.logs.number_of_results',
                           count=self.number_of_results))

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            try:
                search_type = self._map_search_type()
                search_args = self._build_search_args()

                logger.info(i18n.t('components.datastax.hcd.logs.performing_search',
                                   search_type=search_type))
                docs = vector_store.search(
                    query=self.search_query, search_type=search_type, **search_args)
            except Exception as e:
                error_msg = i18n.t('components.datastax.hcd.errors.search_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

            logger.info(i18n.t('components.datastax.hcd.logs.retrieved_documents',
                               count=len(docs)))

            data = docs_to_data(docs)
            logger.info(i18n.t('components.datastax.hcd.logs.converted_to_data',
                               count=len(data)))
            self.status = data
            return data

        logger.info(i18n.t('components.datastax.hcd.logs.no_search_input'))
        return []

    def get_retriever_kwargs(self):
        search_args = self._build_search_args()
        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_args,
        }
