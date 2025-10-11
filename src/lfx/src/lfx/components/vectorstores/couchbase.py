import os
import i18n
from datetime import timedelta

from langchain_community.vectorstores import CouchbaseVectorStore

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import HandleInput, IntInput, SecretStrInput, StrInput
from lfx.schema.data import Data


class CouchbaseVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.vectorstores.couchbase.display_name')
    description = i18n.t('components.vectorstores.couchbase.description')
    name = "Couchbase"
    icon = "Couchbase"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="couchbase_connection_string",
            display_name=i18n.t(
                'components.vectorstores.couchbase.couchbase_connection_string.display_name'),
            required=True
        ),
        StrInput(
            name="couchbase_username",
            display_name=i18n.t(
                'components.vectorstores.couchbase.couchbase_username.display_name'),
            required=True
        ),
        SecretStrInput(
            name="couchbase_password",
            display_name=i18n.t(
                'components.vectorstores.couchbase.couchbase_password.display_name'),
            required=True
        ),
        StrInput(
            name="bucket_name",
            display_name=i18n.t(
                'components.vectorstores.couchbase.bucket_name.display_name'),
            required=True
        ),
        StrInput(
            name="scope_name",
            display_name=i18n.t(
                'components.vectorstores.couchbase.scope_name.display_name'),
            required=True
        ),
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.vectorstores.couchbase.collection_name.display_name'),
            required=True
        ),
        StrInput(
            name="index_name",
            display_name=i18n.t(
                'components.vectorstores.couchbase.index_name.display_name'),
            required=True
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.vectorstores.couchbase.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.vectorstores.couchbase.number_of_results.display_name'),
            info=i18n.t(
                'components.vectorstores.couchbase.number_of_results.info'),
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> CouchbaseVectorStore:
        try:
            from couchbase.auth import PasswordAuthenticator
            from couchbase.cluster import Cluster
            from couchbase.options import ClusterOptions
        except ImportError as e:
            msg = "Failed to import Couchbase dependencies. Install it using `uv pip install langflow[couchbase] --pre`"
            raise ImportError(msg) from e

        try:
            auth = PasswordAuthenticator(
                self.couchbase_username, self.couchbase_password)
            options = ClusterOptions(auth)
            cluster = Cluster(self.couchbase_connection_string, options)

            cluster.wait_until_ready(timedelta(seconds=5))
        except Exception as e:
            msg = f"Failed to connect to Couchbase: {e}"
            raise ValueError(msg) from e

        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        if documents:
            couchbase_vs = CouchbaseVectorStore.from_documents(
                documents=documents,
                cluster=cluster,
                bucket_name=self.bucket_name,
                scope_name=self.scope_name,
                collection_name=self.collection_name,
                embedding=self.embedding,
                index_name=self.index_name,
            )

        else:
            couchbase_vs = CouchbaseVectorStore(
                cluster=cluster,
                bucket_name=self.bucket_name,
                scope_name=self.scope_name,
                collection_name=self.collection_name,
                embedding=self.embedding,
                index_name=self.index_name,
            )

        return couchbase_vs

    def search_documents(self) -> list[Data]:
        vector_store = self.build_vector_store()

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            docs = vector_store.similarity_search(
                query=self.search_query,
                k=self.number_of_results,
            )

            data = docs_to_data(docs)
            self.status = data
            return data
        return []
