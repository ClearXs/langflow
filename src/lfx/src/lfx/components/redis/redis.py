import os
import i18n
from pathlib import Path

from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores.redis import Redis

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import HandleInput, IntInput, SecretStrInput, StrInput
from lfx.schema.data import Data


class RedisVectorStoreComponent(LCVectorStoreComponent):
    """A custom component for implementing a Vector Store using Redis."""

    display_name = i18n.t('components.redis.redis.display_name')
    description = i18n.t('components.redis.redis.description')
    documentation = "https://python.langchain.com/docs/integrations/vectorstores/redis"
    name = "Redis"
    icon = "Redis"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="redis_server_url",
            display_name=i18n.t(
                'components.redis.redis.redis_server_url.display_name'),
            required=True
        ),
        StrInput(
            name="redis_index_name",
            display_name=i18n.t(
                'components.redis.redis.redis_index_name.display_name'),
        ),
        StrInput(
            name="code",
            display_name=i18n.t('components.redis.redis.code.display_name'),
            advanced=True
        ),
        StrInput(
            name="schema",
            display_name=i18n.t('components.redis.redis.schema.display_name'),
        ),
        *LCVectorStoreComponent.inputs,
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.redis.redis.number_of_results.display_name'),
            info=i18n.t('components.redis.redis.number_of_results.info'),
            value=4,
            advanced=True,
        ),
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.redis.redis.embedding.display_name'),
            input_types=["Embeddings"]
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> Redis:
        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)
        Path("docuemnts.txt").write_text(str(documents), encoding="utf-8")

        if not documents:
            if self.schema is None:
                msg = "If no documents are provided, a schema must be provided."
                raise ValueError(msg)
            redis_vs = Redis.from_existing_index(
                embedding=self.embedding,
                index_name=self.redis_index_name,
                schema=self.schema,
                key_prefix=None,
                redis_url=self.redis_server_url,
            )
        else:
            text_splitter = CharacterTextSplitter(
                chunk_size=1000, chunk_overlap=0)
            docs = text_splitter.split_documents(documents)
            redis_vs = Redis.from_documents(
                documents=docs,
                embedding=self.embedding,
                redis_url=self.redis_server_url,
                index_name=self.redis_index_name,
            )
        return redis_vs

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
