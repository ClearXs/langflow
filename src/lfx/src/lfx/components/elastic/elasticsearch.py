import i18n
from typing import Any

from elasticsearch import Elasticsearch
from langchain.schema import Document
from langchain_elasticsearch import ElasticsearchStore

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.io import (
    BoolInput,
    DropdownInput,
    FloatInput,
    HandleInput,
    IntInput,
    SecretStrInput,
    StrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class ElasticsearchVectorStoreComponent(LCVectorStoreComponent):
    """Elasticsearch Vector Store with with advanced, customizable search capabilities."""

    display_name: str = "Elasticsearch"
    description: str = i18n.t('components.elastic.elasticsearch.description')
    name = "Elasticsearch"
    icon = "ElasticsearchStore"

    inputs = [
        StrInput(
            name="elasticsearch_url",
            display_name=i18n.t(
                'components.elastic.elasticsearch.elasticsearch_url.display_name'),
            value="http://localhost:9200",
            info=i18n.t(
                'components.elastic.elasticsearch.elasticsearch_url.info'),
        ),
        SecretStrInput(
            name="cloud_id",
            display_name=i18n.t(
                'components.elastic.elasticsearch.cloud_id.display_name'),
            value="",
            info=i18n.t('components.elastic.elasticsearch.cloud_id.info'),
        ),
        StrInput(
            name="index_name",
            display_name=i18n.t(
                'components.elastic.elasticsearch.index_name.display_name'),
            value="langflow",
            info=i18n.t('components.elastic.elasticsearch.index_name.info'),
        ),
        *LCVectorStoreComponent.inputs,
        StrInput(
            name="username",
            display_name=i18n.t(
                'components.elastic.elasticsearch.username.display_name'),
            value="",
            advanced=False,
            info=i18n.t('components.elastic.elasticsearch.username.info'),
        ),
        SecretStrInput(
            name="password",
            display_name=i18n.t(
                'components.elastic.elasticsearch.password.display_name'),
            value="",
            advanced=False,
            info=i18n.t('components.elastic.elasticsearch.password.info'),
        ),
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.elastic.elasticsearch.embedding.display_name'),
            input_types=["Embeddings"],
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.elastic.elasticsearch.search_type.display_name'),
            options=["similarity", "mmr"],
            value="similarity",
            advanced=True,
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.elastic.elasticsearch.number_of_results.display_name'),
            info=i18n.t(
                'components.elastic.elasticsearch.number_of_results.info'),
            advanced=True,
            value=4,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name=i18n.t(
                'components.elastic.elasticsearch.search_score_threshold.display_name'),
            info=i18n.t(
                'components.elastic.elasticsearch.search_score_threshold.info'),
            value=0.0,
            advanced=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.elastic.elasticsearch.api_key.display_name'),
            value="",
            advanced=True,
            info=i18n.t('components.elastic.elasticsearch.api_key.info'),
        ),
        BoolInput(
            name="verify_certs",
            display_name=i18n.t(
                'components.elastic.elasticsearch.verify_certs.display_name'),
            value=True,
            advanced=True,
            info=i18n.t('components.elastic.elasticsearch.verify_certs.info'),
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> ElasticsearchStore:
        """Builds the Elasticsearch Vector Store object.

        Returns:
            ElasticsearchStore: Configured Elasticsearch vector store.

        Raises:
            ValueError: If both cloud_id and elasticsearch_url are provided.
        """
        if self.cloud_id and self.elasticsearch_url:
            error_msg = i18n.t(
                'components.elastic.elasticsearch.errors.both_cloud_and_url')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.elastic.elasticsearch.logs.building_vector_store',
                           index=self.index_name))

        es_params = {
            "index_name": self.index_name,
            "embedding": self.embedding,
            "es_user": self.username or None,
            "es_password": self.password or None,
        }

        if self.cloud_id:
            es_params["es_cloud_id"] = self.cloud_id
            logger.debug(
                i18n.t('components.elastic.elasticsearch.logs.using_cloud_id'))
        else:
            es_params["es_url"] = self.elasticsearch_url
            logger.debug(i18n.t('components.elastic.elasticsearch.logs.using_url',
                                url=self.elasticsearch_url))

        if self.api_key:
            es_params["api_key"] = self.api_key
            logger.debug(
                i18n.t('components.elastic.elasticsearch.logs.using_api_key'))

        # Check if we need to verify SSL certificates
        if self.verify_certs is False:
            logger.warning(
                i18n.t('components.elastic.elasticsearch.logs.ssl_verification_disabled'))

            # Build client parameters for Elasticsearch constructor
            client_params: dict[str, Any] = {}
            client_params["verify_certs"] = False

            if self.cloud_id:
                client_params["cloud_id"] = self.cloud_id
            else:
                client_params["hosts"] = [self.elasticsearch_url]

            if self.api_key:
                client_params["api_key"] = self.api_key
            elif self.username and self.password:
                client_params["basic_auth"] = (self.username, self.password)

            logger.debug(
                i18n.t('components.elastic.elasticsearch.logs.creating_custom_client'))
            es_client = Elasticsearch(**client_params)
            es_params["es_connection"] = es_client

        try:
            elasticsearch = ElasticsearchStore(**es_params)
            logger.info(
                i18n.t('components.elastic.elasticsearch.logs.vector_store_created'))
        except Exception as e:
            error_msg = i18n.t('components.elastic.elasticsearch.errors.vector_store_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # If documents are provided, add them to the store
        if self.ingest_data:
            documents = self._prepare_documents()
            if documents:
                logger.info(i18n.t('components.elastic.elasticsearch.logs.adding_documents',
                                   count=len(documents)))
                elasticsearch.add_documents(documents)
                logger.info(i18n.t('components.elastic.elasticsearch.logs.documents_added',
                                   count=len(documents)))

        return elasticsearch

    def _prepare_documents(self) -> list[Document]:
        """Prepares documents from the input data to add to the vector store.

        Returns:
            list[Document]: List of prepared documents.

        Raises:
            TypeError: If input data is not Data objects.
        """
        logger.debug(
            i18n.t('components.elastic.elasticsearch.logs.preparing_documents'))
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for data in self.ingest_data:
            if isinstance(data, Data):
                documents.append(data.to_lc_document())
            else:
                error_msg = i18n.t(
                    'components.elastic.elasticsearch.errors.invalid_input_type')
                logger.error(error_msg)
                self.log(error_msg)
                raise TypeError(error_msg)

        logger.debug(i18n.t('components.elastic.elasticsearch.logs.documents_prepared',
                            count=len(documents)))
        return documents

    def _add_documents_to_vector_store(self, vector_store: "ElasticsearchStore") -> None:
        """Adds documents to the Vector Store.

        Args:
            vector_store: The Elasticsearch vector store instance.
        """
        documents = self._prepare_documents()
        if documents and self.embedding:
            log_msg = i18n.t('components.elastic.elasticsearch.logs.adding_documents_to_store',
                             count=len(documents))
            logger.info(log_msg)
            self.log(log_msg)
            vector_store.add_documents(documents)
            logger.info(
                i18n.t('components.elastic.elasticsearch.logs.documents_added_successfully'))
        else:
            log_msg = i18n.t(
                'components.elastic.elasticsearch.logs.no_documents_to_add')
            logger.info(log_msg)
            self.log(log_msg)

    def search(self, query: str | None = None) -> list[dict[str, Any]]:
        """Search for similar documents in the vector store or retrieve all documents if no query is provided.

        Args:
            query: The search query string. If None, retrieves all documents.

        Returns:
            list[dict[str, Any]]: List of search results with content, metadata, and scores.

        Raises:
            ValueError: If search type is invalid or search fails.
        """
        vector_store = self.build_vector_store()
        search_kwargs = {
            "k": self.number_of_results,
            "score_threshold": self.search_score_threshold,
        }

        if query:
            logger.info(i18n.t('components.elastic.elasticsearch.logs.searching_with_query',
                               query=query[:100] + ("..." if len(query) > 100 else "")))

            search_type = self.search_type.lower()
            if search_type not in {"similarity", "mmr"}:
                error_msg = i18n.t('components.elastic.elasticsearch.errors.invalid_search_type',
                                   search_type=self.search_type)
                logger.error(error_msg)
                self.log(error_msg)
                raise ValueError(error_msg)

            try:
                if search_type == "similarity":
                    logger.debug(
                        i18n.t('components.elastic.elasticsearch.logs.performing_similarity_search'))
                    results = vector_store.similarity_search_with_score(
                        query, **search_kwargs)
                elif search_type == "mmr":
                    logger.debug(
                        i18n.t('components.elastic.elasticsearch.logs.performing_mmr_search'))
                    results = vector_store.max_marginal_relevance_search(
                        query, **search_kwargs)
            except Exception as e:
                error_msg = i18n.t(
                    'components.elastic.elasticsearch.errors.search_failed')
                logger.exception(error_msg)
                self.log(error_msg)
                raise ValueError(error_msg) from e

            logger.info(i18n.t('components.elastic.elasticsearch.logs.search_completed',
                               count=len(results)))
            return [
                {"page_content": doc.page_content, "metadata": doc.metadata, "score": score} for doc, score in results
            ]

        logger.info(
            i18n.t('components.elastic.elasticsearch.logs.retrieving_all_documents'))
        results = self.get_all_documents(vector_store, **search_kwargs)
        logger.info(i18n.t('components.elastic.elasticsearch.logs.all_documents_retrieved',
                           count=len(results)))
        return [{"page_content": doc.page_content, "metadata": doc.metadata, "score": score} for doc, score in results]

    def get_all_documents(self, vector_store: ElasticsearchStore, **kwargs) -> list[tuple[Document, float]]:
        """Retrieve all documents from the vector store.

        Args:
            vector_store: The Elasticsearch vector store instance.
            **kwargs: Additional search parameters.

        Returns:
            list[tuple[Document, float]]: List of documents with their scores.
        """
        logger.debug(
            i18n.t('components.elastic.elasticsearch.logs.getting_all_documents'))

        client = vector_store.client
        index_name = self.index_name

        query = {
            "query": {"match_all": {}},
            "size": kwargs.get("k", self.number_of_results),
        }

        try:
            response = client.search(index=index_name, body=query)
            logger.debug(i18n.t('components.elastic.elasticsearch.logs.search_response_received',
                                hits=len(response["hits"]["hits"])))
        except Exception as e:
            error_msg = i18n.t('components.elastic.elasticsearch.errors.get_all_failed',
                               error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        results = []
        for hit in response["hits"]["hits"]:
            doc = Document(
                page_content=hit["_source"].get("text", ""),
                metadata=hit["_source"].get("metadata", {}),
            )
            score = hit["_score"]
            results.append((doc, score))

        logger.debug(i18n.t('components.elastic.elasticsearch.logs.documents_retrieved',
                            count=len(results)))
        return results

    def search_documents(self) -> list[Data]:
        """Search for documents in the vector store based on the search input.

        If no search input is provided, retrieve all documents.

        Returns:
            list[Data]: List of retrieved documents.
        """
        logger.info(
            i18n.t('components.elastic.elasticsearch.logs.starting_search'))

        results = self.search(self.search_query)
        retrieved_data = [
            Data(
                text=result["page_content"],
                file_path=result["metadata"].get("file_path", ""),
            )
            for result in results
        ]

        logger.info(i18n.t('components.elastic.elasticsearch.logs.search_documents_completed',
                           count=len(retrieved_data)))
        self.status = retrieved_data
        return retrieved_data

    def get_retriever_kwargs(self):
        """Get the keyword arguments for the retriever.

        Returns:
            dict: Dictionary of retriever configuration.
        """
        return {
            "search_type": self.search_type.lower(),
            "search_kwargs": {
                "k": self.number_of_results,
                "score_threshold": self.search_score_threshold,
            },
        }
