import os
import i18n
from langchain_community.vectorstores import PGVector

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import HandleInput, IntInput, SecretStrInput, StrInput
from lfx.schema.data import Data
from lfx.utils.connection_string_parser import transform_connection_string


class PGVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.pgvector.pgvector.display_name')
    description = i18n.t('components.pgvector.pgvector.description')
    documentation = "https://python.langchain.com/docs/integrations/vectorstores/pgvector"
    name = "pgvector"
    icon = "cpu"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="pg_server_url",
            display_name=i18n.t(
                'components.pgvector.pgvector.pg_server_url.display_name'),
            info=i18n.t('components.pgvector.pgvector.pg_server_url.info'),
            required=True
        ),
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.pgvector.pgvector.collection_name.display_name'),
            info=i18n.t('components.pgvector.pgvector.collection_name.info'),
            required=True
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.pgvector.pgvector.embedding.display_name'),
            input_types=["Embeddings"],
            required=True
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.pgvector.pgvector.number_of_results.display_name'),
            info=i18n.t('components.pgvector.pgvector.number_of_results.info'),
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> PGVector:
        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        connection_string_parsed = transform_connection_string(
            self.pg_server_url)

        if documents:
            pgvector = PGVector.from_documents(
                embedding=self.embedding,
                documents=documents,
                collection_name=self.collection_name,
                connection_string=connection_string_parsed,
            )
        else:
            pgvector = PGVector.from_existing_index(
                embedding=self.embedding,
                collection_name=self.collection_name,
                connection_string=connection_string_parsed,
            )

        return pgvector

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
