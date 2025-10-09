from datetime import timedelta

import i18n
from langchain_community.vectorstores import CouchbaseVectorStore

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import HandleInput, IntInput, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class CouchbaseVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.couchbase.couchbase.display_name')
    description = i18n.t('components.couchbase.couchbase.description')
    name = "Couchbase"
    icon = "Couchbase"
    documentation = "https://docs.couchbase.com/python-sdk/current/howtos/full-text-searching-with-sdk.html"

    inputs = [
        SecretStrInput(
            name="couchbase_connection_string",
            display_name=i18n.t(
                'components.couchbase.couchbase.connection_string.display_name'),
            info=i18n.t(
                'components.couchbase.couchbase.connection_string.info'),
            required=True
        ),
        StrInput(
            name="couchbase_username",
            display_name=i18n.t(
                'components.couchbase.couchbase.username.display_name'),
            info=i18n.t('components.couchbase.couchbase.username.info'),
            required=True
        ),
        SecretStrInput(
            name="couchbase_password",
            display_name=i18n.t(
                'components.couchbase.couchbase.password.display_name'),
            info=i18n.t('components.couchbase.couchbase.password.info'),
            required=True
        ),
        StrInput(
            name="bucket_name",
            display_name=i18n.t(
                'components.couchbase.couchbase.bucket_name.display_name'),
            info=i18n.t('components.couchbase.couchbase.bucket_name.info'),
            required=True
        ),
        StrInput(
            name="scope_name",
            display_name=i18n.t(
                'components.couchbase.couchbase.scope_name.display_name'),
            info=i18n.t('components.couchbase.couchbase.scope_name.info'),
            required=True
        ),
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.couchbase.couchbase.collection_name.display_name'),
            info=i18n.t('components.couchbase.couchbase.collection_name.info'),
            required=True
        ),
        StrInput(
            name="index_name",
            display_name=i18n.t(
                'components.couchbase.couchbase.index_name.display_name'),
            info=i18n.t('components.couchbase.couchbase.index_name.info'),
            required=True
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.couchbase.couchbase.embedding.display_name'),
            info=i18n.t('components.couchbase.couchbase.embedding.info'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.couchbase.couchbase.number_of_results.display_name'),
            info=i18n.t(
                'components.couchbase.couchbase.number_of_results.info'),
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> CouchbaseVectorStore:
        """Build and configure Couchbase vector store.

        Returns:
            CouchbaseVectorStore: Configured Couchbase vector store instance.

        Raises:
            ImportError: If Couchbase dependencies are not installed.
            ValueError: If connection to Couchbase fails.
        """
        try:
            from couchbase.auth import PasswordAuthenticator
            from couchbase.cluster import Cluster
            from couchbase.options import ClusterOptions

            logger.debug(
                i18n.t('components.couchbase.couchbase.logs.imports_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.couchbase.couchbase.errors.import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            logger.info(i18n.t('components.couchbase.couchbase.logs.connecting',
                               connection_string=self.couchbase_connection_string))
            self.status = i18n.t(
                'components.couchbase.couchbase.status.connecting')

            auth = PasswordAuthenticator(
                self.couchbase_username, self.couchbase_password)
            options = ClusterOptions(auth)
            cluster = Cluster(self.couchbase_connection_string, options)

            logger.debug(
                i18n.t('components.couchbase.couchbase.logs.waiting_for_ready'))
            cluster.wait_until_ready(timedelta(seconds=5))

            logger.info(
                i18n.t('components.couchbase.couchbase.logs.connection_successful'))

        except Exception as e:
            error_msg = i18n.t('components.couchbase.couchbase.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e

        try:
            logger.debug(
                i18n.t('components.couchbase.couchbase.logs.preparing_data'))
            self.ingest_data = self._prepare_ingest_data()

            documents = []
            for _input in self.ingest_data or []:
                if isinstance(_input, Data):
                    documents.append(_input.to_lc_document())
                else:
                    documents.append(_input)

            logger.info(i18n.t('components.couchbase.couchbase.logs.documents_prepared',
                               count=len(documents)))

            if documents:
                logger.info(i18n.t('components.couchbase.couchbase.logs.creating_from_documents',
                                   count=len(documents),
                                   bucket=self.bucket_name,
                                   collection=self.collection_name))
                self.status = i18n.t('components.couchbase.couchbase.status.creating_with_documents',
                                     count=len(documents))

                couchbase_vs = CouchbaseVectorStore.from_documents(
                    documents=documents,
                    cluster=cluster,
                    bucket_name=self.bucket_name,
                    scope_name=self.scope_name,
                    collection_name=self.collection_name,
                    embedding=self.embedding,
                    index_name=self.index_name,
                )

                logger.info(i18n.t('components.couchbase.couchbase.logs.store_created_with_documents',
                                   count=len(documents)))
            else:
                logger.info(i18n.t('components.couchbase.couchbase.logs.creating_empty_store',
                                   bucket=self.bucket_name,
                                   collection=self.collection_name))
                self.status = i18n.t(
                    'components.couchbase.couchbase.status.creating_empty')

                couchbase_vs = CouchbaseVectorStore(
                    cluster=cluster,
                    bucket_name=self.bucket_name,
                    scope_name=self.scope_name,
                    collection_name=self.collection_name,
                    embedding=self.embedding,
                    index_name=self.index_name,
                )

                logger.info(
                    i18n.t('components.couchbase.couchbase.logs.empty_store_created'))

            success_msg = i18n.t('components.couchbase.couchbase.status.build_successful',
                                 bucket=self.bucket_name,
                                 collection=self.collection_name,
                                 index=self.index_name)
            self.status = success_msg
            logger.info(success_msg)

            return couchbase_vs

        except Exception as e:
            error_msg = i18n.t('components.couchbase.couchbase.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e

    def search_documents(self) -> list[Data]:
        """Search for similar documents in Couchbase vector store.

        Returns:
            list[Data]: List of similar documents as Data objects.
        """
        try:
            logger.info(
                i18n.t('components.couchbase.couchbase.logs.building_for_search'))
            self.status = i18n.t(
                'components.couchbase.couchbase.status.initializing_search')

            vector_store = self.build_vector_store()

            if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
                logger.info(i18n.t('components.couchbase.couchbase.logs.searching',
                                   query=self.search_query[:50],
                                   k=self.number_of_results))
                self.status = i18n.t(
                    'components.couchbase.couchbase.status.searching')

                docs = vector_store.similarity_search(
                    query=self.search_query,
                    k=self.number_of_results,
                )

                logger.info(i18n.t('components.couchbase.couchbase.logs.search_completed',
                                   count=len(docs)))

                data = docs_to_data(docs)

                success_msg = i18n.t('components.couchbase.couchbase.status.search_successful',
                                     count=len(data))
                self.status = success_msg
                logger.info(success_msg)

                return data

            warning_msg = i18n.t(
                'components.couchbase.couchbase.warnings.empty_query')
            logger.warning(warning_msg)
            self.status = warning_msg
            return []

        except Exception as e:
            error_msg = i18n.t('components.couchbase.couchbase.errors.search_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
