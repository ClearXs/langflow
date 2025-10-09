import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field

import i18n
from astrapy import DataAPIClient, Database
from astrapy.data.info.reranking import RerankServiceOptions
from astrapy.info import CollectionDescriptor, CollectionLexicalOptions, CollectionRerankOptions
from langchain_astradb import AstraDBVectorStore, VectorServiceOptions
from langchain_astradb.utils.astradb import HybridSearchMode, _AstraDBCollectionEnvironment
from langchain_core.documents import Document

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.base.vectorstores.vector_store_connection_decorator import vector_store_connection
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import FloatInput, NestedDictInput
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    IntInput,
    QueryInput,
    SecretStrInput,
    StrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.serialization import serialize
from lfx.utils.version import get_version_info


@vector_store_connection
class AstraDBVectorStoreComponent(LCVectorStoreComponent):
    display_name: str = i18n.t(
        'components.datastax.astradb_vectorstore.display_name')
    description: str = i18n.t(
        'components.datastax.astradb_vectorstore.description')
    documentation: str = "https://docs.datastax.com/en/langflow/astra-components.html"
    name = "AstraDB"
    icon: str = "AstraDB"

    _cached_vector_store: AstraDBVectorStore | None = None

    @dataclass
    class NewDatabaseInput:
        functionality: str = "create"
        fields: dict[str, dict] = field(
            default_factory=lambda: {
                "data": {
                    "node": {
                        "name": "create_database",
                        "description": i18n.t('components.datastax.astradb_vectorstore.new_database.description'),
                        "display_name": i18n.t('components.datastax.astradb_vectorstore.new_database.display_name'),
                        "field_order": ["01_new_database_name", "02_cloud_provider", "03_region"],
                        "template": {
                            "01_new_database_name": StrInput(
                                name="new_database_name",
                                display_name=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_database.name.display_name'),
                                info=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_database.name.info'),
                                required=True,
                            ),
                            "02_cloud_provider": DropdownInput(
                                name="cloud_provider",
                                display_name=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_database.cloud_provider.display_name'),
                                info=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_database.cloud_provider.info'),
                                options=[],
                                required=True,
                                real_time_refresh=True,
                            ),
                            "03_region": DropdownInput(
                                name="region",
                                display_name=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_database.region.display_name'),
                                info=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_database.region.info'),
                                options=[],
                                required=True,
                            ),
                        },
                    },
                }
            }
        )

    @dataclass
    class NewCollectionInput:
        functionality: str = "create"
        fields: dict[str, dict] = field(
            default_factory=lambda: {
                "data": {
                    "node": {
                        "name": "create_collection",
                        "description": i18n.t('components.datastax.astradb_vectorstore.new_collection.description'),
                        "display_name": i18n.t('components.datastax.astradb_vectorstore.new_collection.display_name'),
                        "field_order": [
                            "01_new_collection_name",
                            "02_embedding_generation_provider",
                            "03_embedding_generation_model",
                            "04_dimension",
                        ],
                        "template": {
                            "01_new_collection_name": StrInput(
                                name="new_collection_name",
                                display_name=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.name.display_name'),
                                info=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.name.info'),
                                required=True,
                            ),
                            "02_embedding_generation_provider": DropdownInput(
                                name="embedding_generation_provider",
                                display_name=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.provider.display_name'),
                                info=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.provider.info'),
                                helper_text=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.provider.helper_text'),
                                real_time_refresh=True,
                                required=True,
                                options=[],
                            ),
                            "03_embedding_generation_model": DropdownInput(
                                name="embedding_generation_model",
                                display_name=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.model.display_name'),
                                info=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.model.info'),
                                real_time_refresh=True,
                                options=[],
                            ),
                            "04_dimension": IntInput(
                                name="dimension",
                                display_name=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.dimension.display_name'),
                                info=i18n.t(
                                    'components.datastax.astradb_vectorstore.new_collection.dimension.info'),
                                value=None,
                            ),
                        },
                    },
                }
            }
        )

    inputs = [
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.token.display_name'),
            info=i18n.t('components.datastax.astradb_vectorstore.token.info'),
            value="ASTRA_DB_APPLICATION_TOKEN",
            required=True,
            real_time_refresh=True,
            input_types=[],
        ),
        DropdownInput(
            name="environment",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.environment.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.environment.info'),
            options=["prod", "test", "dev"],
            value="prod",
            advanced=True,
            real_time_refresh=True,
            combobox=True,
        ),
        DropdownInput(
            name="database_name",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.database_name.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.database_name.info'),
            required=True,
            refresh_button=True,
            real_time_refresh=True,
            dialog_inputs=asdict(NewDatabaseInput()),
            combobox=True,
        ),
        DropdownInput(
            name="api_endpoint",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.api_endpoint.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.api_endpoint.info'),
            advanced=True,
        ),
        DropdownInput(
            name="keyspace",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.keyspace.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.keyspace.info'),
            advanced=True,
            options=[],
            real_time_refresh=True,
        ),
        DropdownInput(
            name="collection_name",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.collection_name.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.collection_name.info'),
            required=True,
            refresh_button=True,
            real_time_refresh=True,
            dialog_inputs=asdict(NewCollectionInput()),
            combobox=True,
            show=False,
        ),
        HandleInput(
            name="embedding_model",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.embedding_model.display_name'),
            input_types=["Embeddings"],
            info=i18n.t(
                'components.datastax.astradb_vectorstore.embedding_model.info'),
            required=False,
            show=True,
        ),
        *LCVectorStoreComponent.inputs,
        DropdownInput(
            name="search_method",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.search_method.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.search_method.info'),
            options=["Hybrid Search", "Vector Search"],
            options_metadata=[{"icon": "SearchHybrid"},
                              {"icon": "SearchVector"}],
            value="Vector Search",
            advanced=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="reranker",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.reranker.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.reranker.info'),
            show=False,
            toggle=True,
        ),
        QueryInput(
            name="lexical_terms",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.lexical_terms.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.lexical_terms.info'),
            placeholder=i18n.t(
                'components.datastax.astradb_vectorstore.lexical_terms.placeholder'),
            separator=" ",
            show=False,
            value="",
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.number_of_results.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.number_of_results.info'),
            advanced=True,
            value=4,
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.search_type.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.search_type.info'),
            options=["Similarity", "Similarity with score threshold",
                     "MMR (Max Marginal Relevance)"],
            value="Similarity",
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.search_score_threshold.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.search_score_threshold.info'),
            value=0,
            advanced=True,
        ),
        NestedDictInput(
            name="advanced_search_filter",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.advanced_search_filter.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.advanced_search_filter.info'),
            advanced=True,
        ),
        BoolInput(
            name="autodetect_collection",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.autodetect_collection.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.autodetect_collection.info'),
            advanced=True,
            value=True,
        ),
        StrInput(
            name="content_field",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.content_field.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.content_field.info'),
            advanced=True,
        ),
        StrInput(
            name="deletion_field",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.deletion_field.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.deletion_field.info'),
            advanced=True,
        ),
        BoolInput(
            name="ignore_invalid_documents",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.ignore_invalid_documents.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.ignore_invalid_documents.info'),
            advanced=True,
        ),
        NestedDictInput(
            name="astradb_vectorstore_kwargs",
            display_name=i18n.t(
                'components.datastax.astradb_vectorstore.astradb_vectorstore_kwargs.display_name'),
            info=i18n.t(
                'components.datastax.astradb_vectorstore.astradb_vectorstore_kwargs.info'),
            advanced=True,
        ),
    ]

    # ... [保持所有现有方法，添加日志翻译] ...

    @classmethod
    async def create_database_api(cls, new_database_name: str, cloud_provider: str, region: str,
                                  token: str, environment: str | None = None, keyspace: str | None = None):
        client = DataAPIClient(environment=environment)
        admin_client = client.get_admin(token=token)
        my_env = environment or "prod"

        if not new_database_name:
            error_msg = i18n.t(
                'components.datastax.astradb_vectorstore.errors.database_name_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.creating_database',
                           name=new_database_name,
                           provider=cloud_provider,
                           region=region))

        return await admin_client.async_create_database(
            name=new_database_name,
            cloud_provider=cls.map_cloud_providers(
            )[my_env][cloud_provider]["id"],
            region=region,
            keyspace=keyspace,
            wait_until_active=False,
        )

    @classmethod
    async def create_collection_api(cls, new_collection_name: str, token: str, api_endpoint: str,
                                    environment: str | None = None, keyspace: str | None = None,
                                    dimension: int | None = None, embedding_generation_provider: str | None = None,
                                    embedding_generation_model: str | None = None, reranker: str | None = None):
        vectorize_options = None
        if not dimension:
            providers = cls.get_vectorize_providers(
                token=token, environment=environment, api_endpoint=api_endpoint)
            vectorize_options = VectorServiceOptions(
                provider=providers.get(
                    embedding_generation_provider, [None, []])[0],
                model_name=embedding_generation_model,
            )

        if not new_collection_name:
            error_msg = i18n.t(
                'components.datastax.astradb_vectorstore.errors.collection_name_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.creating_collection',
                           name=new_collection_name))

        base_args = {
            "collection_name": new_collection_name,
            "token": token,
            "api_endpoint": api_endpoint,
            "keyspace": keyspace,
            "environment": environment,
            "embedding_dimension": dimension,
            "collection_vector_service_options": vectorize_options,
        }

        if reranker:
            provider, _ = reranker.split("/")
            base_args["collection_rerank"] = CollectionRerankOptions(
                service=RerankServiceOptions(
                    provider=provider, model_name=reranker),
            )
            base_args["collection_lexical"] = CollectionLexicalOptions(
                analyzer="STANDARD")
            logger.debug(i18n.t('components.datastax.astradb_vectorstore.logs.reranker_configured',
                                reranker=reranker))

        _AstraDBCollectionEnvironment(**base_args)

    def get_database_object(self, api_endpoint: str | None = None):
        try:
            client = DataAPIClient(environment=self.environment)
            database = client.get_database(
                api_endpoint or self.get_api_endpoint(),
                token=self.token,
                keyspace=self.get_keyspace(),
            )
            logger.debug(
                i18n.t('components.datastax.astradb_vectorstore.logs.database_object_created'))
            return database
        except Exception as e:
            error_msg = i18n.t('components.datastax.astradb_vectorstore.errors.fetch_database_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def collection_data(self, collection_name: str, database: Database | None = None):
        try:
            if not database:
                client = DataAPIClient(environment=self.environment)
                database = client.get_database(
                    self.get_api_endpoint(),
                    token=self.token,
                    keyspace=self.get_keyspace(),
                )

            collection = database.get_collection(collection_name)
            count = collection.estimated_document_count()
            logger.debug(i18n.t('components.datastax.astradb_vectorstore.logs.collection_count',
                                collection=collection_name,
                                count=count))
            return count
        except Exception as e:
            logger.warning(i18n.t('components.datastax.astradb_vectorstore.logs.collection_count_error',
                                  error=str(e)))
            return None

    @check_cached_vector_store
    def build_vector_store(self):
        try:
            from langchain_astradb import AstraDBVectorStore
            logger.debug(i18n.t(
                'components.datastax.astradb_vectorstore.logs.langchain_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.datastax.astradb_vectorstore.errors.langchain_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.building_vector_store',
                           collection=self.collection_name))

        embedding_params = {
            "embedding": self.embedding_model} if self.embedding_model else {}
        additional_params = self.astradb_vectorstore_kwargs or {}

        __version__ = get_version_info()["version"]
        langflow_prefix = ""

        database = self.get_database_object()
        autodetect = self.collection_name in database.list_collection_names(
        ) and self.autodetect_collection

        autodetect_params = {
            "autodetect_collection": autodetect,
            "content_field": (
                self.content_field
                if self.content_field and embedding_params
                else (
                    "page_content"
                    if embedding_params
                    and self.collection_data(collection_name=self.collection_name, database=database) == 0
                    else None
                )
            ),
            "ignore_invalid_documents": self.ignore_invalid_documents,
        }

        hybrid_search_mode = HybridSearchMode.DEFAULT if self.search_method == "Hybrid Search" else HybridSearchMode.OFF
        logger.debug(i18n.t('components.datastax.astradb_vectorstore.logs.hybrid_search_mode',
                            mode=self.search_method))

        try:
            vector_store = AstraDBVectorStore(
                token=self.token,
                api_endpoint=database.api_endpoint,
                namespace=database.keyspace,
                collection_name=self.collection_name,
                environment=self.environment,
                hybrid_search=hybrid_search_mode,
                ext_callers=[(f"{langflow_prefix}langflow", __version__)],
                **autodetect_params,
                **embedding_params,
                **additional_params,
            )
            logger.info(
                i18n.t('components.datastax.astradb_vectorstore.logs.vector_store_initialized'))
        except Exception as e:
            error_msg = i18n.t('components.datastax.astradb_vectorstore.errors.initialization_failed',
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
                    'components.datastax.astradb_vectorstore.errors.invalid_input_type')
                logger.error(error_msg)
                raise TypeError(error_msg)

        documents = [
            Document(page_content=doc.page_content, metadata=serialize(doc.metadata, to_str=True)) for doc in documents
        ]

        if documents and self.deletion_field:
            logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.deleting_by_field',
                               field=self.deletion_field))
            try:
                database = self.get_database_object()
                collection = database.get_collection(
                    self.collection_name, keyspace=database.keyspace)
                delete_values = list(
                    {doc.metadata[self.deletion_field] for doc in documents})
                logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.deleting_values',
                                   field=self.deletion_field,
                                   values=str(delete_values)))
                collection.delete_many(
                    {f"metadata.{self.deletion_field}": {"$in": delete_values}})
            except Exception as e:
                error_msg = i18n.t('components.datastax.astradb_vectorstore.errors.deletion_failed',
                                   field=self.deletion_field,
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

        if documents:
            logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.adding_documents',
                               count=len(documents)))
            try:
                vector_store.add_documents(documents)
                logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.documents_added',
                                   count=len(documents)))
            except Exception as e:
                error_msg = i18n.t('components.datastax.astradb_vectorstore.errors.add_documents_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e
        else:
            logger.info(
                i18n.t('components.datastax.astradb_vectorstore.logs.no_documents'))

    def search_documents(self, vector_store=None) -> list[Data]:
        vector_store = vector_store or self.build_vector_store()

        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.search_input',
                           query=self.search_query))
        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.search_type_log',
                           search_type=self.search_type))
        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.number_of_results',
                           count=self.number_of_results))
        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.hybrid_search_status',
                           status=vector_store.hybrid_search))
        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.lexical_terms_log',
                           terms=self.lexical_terms))
        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.reranker_log',
                           reranker=self.reranker))

        try:
            search_args = self._build_search_args()
        except Exception as e:
            error_msg = i18n.t('components.datastax.astradb_vectorstore.errors.build_search_args_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        if not search_args:
            logger.info(
                i18n.t('components.datastax.astradb_vectorstore.logs.no_search_input'))
            return []

        docs = []
        search_method = "search" if "query" in search_args else "metadata_search"

        try:
            logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.calling_search_method',
                               method=search_method,
                               args=str(search_args)))
            docs = getattr(vector_store, search_method)(**search_args)
        except Exception as e:
            error_msg = i18n.t('components.datastax.astradb_vectorstore.errors.search_failed',
                               method=search_method,
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.retrieved_documents',
                           count=len(docs)))

        data = docs_to_data(docs)
        logger.info(i18n.t('components.datastax.astradb_vectorstore.logs.converted_to_data',
                           count=len(data)))
        self.status = data

        return data

    def get_retriever_kwargs(self):
        search_args = self._build_search_args()
        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_args,
        }
