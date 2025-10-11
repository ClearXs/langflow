import os
import i18n
from langchain.embeddings.base import Embeddings
from langchain_community.vectorstores import Qdrant

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import (
    DropdownInput,
    HandleInput,
    IntInput,
    SecretStrInput,
    StrInput,
)
from lfx.schema.data import Data


class QdrantVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.qdrant.qdrant.display_name')
    description = i18n.t('components.qdrant.qdrant.description')
    documentation = "https://python.langchain.com/docs/integrations/vectorstores/qdrant"
    icon = "Qdrant"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.qdrant.qdrant.collection_name.display_name'),
            required=True
        ),
        StrInput(
            name="host",
            display_name=i18n.t('components.qdrant.qdrant.host.display_name'),
            value="localhost",
            advanced=True
        ),
        IntInput(
            name="port",
            display_name=i18n.t('components.qdrant.qdrant.port.display_name'),
            value=6333,
            advanced=True
        ),
        IntInput(
            name="grpc_port",
            display_name=i18n.t(
                'components.qdrant.qdrant.grpc_port.display_name'),
            value=6334,
            advanced=True
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.qdrant.qdrant.api_key.display_name'),
            advanced=True
        ),
        StrInput(
            name="prefix",
            display_name=i18n.t(
                'components.qdrant.qdrant.prefix.display_name'),
            advanced=True
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.qdrant.qdrant.timeout.display_name'),
            advanced=True
        ),
        StrInput(
            name="path",
            display_name=i18n.t('components.qdrant.qdrant.path.display_name'),
            advanced=True
        ),
        StrInput(
            name="url",
            display_name=i18n.t('components.qdrant.qdrant.url.display_name'),
            advanced=True
        ),
        DropdownInput(
            name="distance_func",
            display_name=i18n.t(
                'components.qdrant.qdrant.distance_func.display_name'),
            options=["Cosine", "Euclidean", "Dot Product"],
            value="Cosine",
            advanced=True,
        ),
        StrInput(
            name="content_payload_key",
            display_name=i18n.t(
                'components.qdrant.qdrant.content_payload_key.display_name'),
            value="page_content",
            advanced=True
        ),
        StrInput(
            name="metadata_payload_key",
            display_name=i18n.t(
                'components.qdrant.qdrant.metadata_payload_key.display_name'),
            value="metadata",
            advanced=True
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.qdrant.qdrant.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.qdrant.qdrant.number_of_results.display_name'),
            info=i18n.t('components.qdrant.qdrant.number_of_results.info'),
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> Qdrant:
        qdrant_kwargs = {
            "collection_name": self.collection_name,
            "content_payload_key": self.content_payload_key,
            "metadata_payload_key": self.metadata_payload_key,
        }

        server_kwargs = {
            "host": self.host or None,
            "port": int(self.port),  # Ensure port is an integer
            "grpc_port": int(self.grpc_port),  # Ensure grpc_port is an integer
            "api_key": self.api_key,
            "prefix": self.prefix,
            # Ensure timeout is an integer
            "timeout": int(self.timeout) if self.timeout else None,
            "path": self.path or None,
            "url": self.url or None,
        }

        server_kwargs = {k: v for k,
                         v in server_kwargs.items() if v is not None}

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        if not isinstance(self.embedding, Embeddings):
            msg = "Invalid embedding object"
            raise TypeError(msg)

        if documents:
            qdrant = Qdrant.from_documents(
                documents, embedding=self.embedding, **qdrant_kwargs, **server_kwargs)
        else:
            from qdrant_client import QdrantClient

            client = QdrantClient(**server_kwargs)
            qdrant = Qdrant(embeddings=self.embedding,
                            client=client, **qdrant_kwargs)

        return qdrant

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
