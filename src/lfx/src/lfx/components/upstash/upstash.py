import os
import i18n
from langchain_community.vectorstores import UpstashVectorStore

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import (
    HandleInput,
    IntInput,
    MultilineInput,
    SecretStrInput,
    StrInput,
)
from lfx.schema.data import Data


class UpstashVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.upstash.upstash.display_name')
    description = i18n.t('components.upstash.upstash.description')
    name = "Upstash"
    icon = "Upstash"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="index_url",
            display_name=i18n.t(
                'components.upstash.upstash.index_url.display_name'),
            info=i18n.t('components.upstash.upstash.index_url.info'),
            required=True,
        ),
        SecretStrInput(
            name="index_token",
            display_name=i18n.t(
                'components.upstash.upstash.index_token.display_name'),
            info=i18n.t('components.upstash.upstash.index_token.info'),
            required=True,
        ),
        StrInput(
            name="text_key",
            display_name=i18n.t(
                'components.upstash.upstash.text_key.display_name'),
            info=i18n.t('components.upstash.upstash.text_key.info'),
            value="text",
            advanced=True,
        ),
        StrInput(
            name="namespace",
            display_name=i18n.t(
                'components.upstash.upstash.namespace.display_name'),
            info=i18n.t('components.upstash.upstash.namespace.info'),
        ),
        *LCVectorStoreComponent.inputs,
        MultilineInput(
            name="metadata_filter",
            display_name=i18n.t(
                'components.upstash.upstash.metadata_filter.display_name'),
            info=i18n.t('components.upstash.upstash.metadata_filter.info'),
        ),
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.upstash.upstash.embedding.display_name'),
            input_types=["Embeddings"],
            info=i18n.t('components.upstash.upstash.embedding.info'),
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.upstash.upstash.number_of_results.display_name'),
            info=i18n.t('components.upstash.upstash.number_of_results.info'),
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> UpstashVectorStore:
        use_upstash_embedding = self.embedding is None

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        if documents:
            if use_upstash_embedding:
                upstash_vs = UpstashVectorStore(
                    embedding=use_upstash_embedding,
                    text_key=self.text_key,
                    index_url=self.index_url,
                    index_token=self.index_token,
                    namespace=self.namespace,
                )
                upstash_vs.add_documents(documents)
            else:
                upstash_vs = UpstashVectorStore.from_documents(
                    documents=documents,
                    embedding=self.embedding,
                    text_key=self.text_key,
                    index_url=self.index_url,
                    index_token=self.index_token,
                    namespace=self.namespace,
                )
        else:
            upstash_vs = UpstashVectorStore(
                embedding=self.embedding or use_upstash_embedding,
                text_key=self.text_key,
                index_url=self.index_url,
                index_token=self.index_token,
                namespace=self.namespace,
            )

        return upstash_vs

    def search_documents(self) -> list[Data]:
        vector_store = self.build_vector_store()

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            docs = vector_store.similarity_search(
                query=self.search_query,
                k=self.number_of_results,
                filter=self.metadata_filter,
            )

            data = docs_to_data(docs)
            self.status = data
            return data
        return []
