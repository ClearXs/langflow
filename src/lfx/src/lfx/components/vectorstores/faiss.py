import os
import i18n
from pathlib import Path

from langchain_community.vectorstores import FAISS

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import BoolInput, HandleInput, IntInput, StrInput
from lfx.schema.data import Data


class FaissVectorStoreComponent(LCVectorStoreComponent):
    """FAISS Vector Store with search capabilities."""

    display_name: str = i18n.t('components.vectorstores.faiss.display_name')
    description: str = i18n.t('components.vectorstores.faiss.description')
    name = "FAISS"
    icon = "FAISS"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="index_name",
            display_name=i18n.t(
                'components.vectorstores.faiss.index_name.display_name'),
            value="langflow_index",
        ),
        StrInput(
            name="persist_directory",
            display_name=i18n.t(
                'components.vectorstores.faiss.persist_directory.display_name'),
            info=i18n.t(
                'components.vectorstores.faiss.persist_directory.info'),
        ),
        *LCVectorStoreComponent.inputs,
        BoolInput(
            name="allow_dangerous_deserialization",
            display_name=i18n.t(
                'components.vectorstores.faiss.allow_dangerous_deserialization.display_name'),
            info=i18n.t(
                'components.vectorstores.faiss.allow_dangerous_deserialization.info'),
            advanced=True,
            value=True,
        ),
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.vectorstores.faiss.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.vectorstores.faiss.number_of_results.display_name'),
            info=i18n.t(
                'components.vectorstores.faiss.number_of_results.info'),
            advanced=True,
            value=4,
        ),
    ]

    @staticmethod
    def resolve_path(path: str) -> str:
        """Resolve the path relative to the Langflow root.

        Args:
            path: The path to resolve
        Returns:
            str: The resolved path as a string
        """
        return str(Path(path).resolve())

    def get_persist_directory(self) -> Path:
        """Returns the resolved persist directory path or the current directory if not set."""
        if self.persist_directory:
            return Path(self.resolve_path(self.persist_directory))
        return Path()

    @check_cached_vector_store
    def build_vector_store(self) -> FAISS:
        """Builds the FAISS object."""
        path = self.get_persist_directory()
        path.mkdir(parents=True, exist_ok=True)

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        faiss = FAISS.from_documents(
            documents=documents, embedding=self.embedding)
        faiss.save_local(str(path), self.index_name)
        return faiss

    def search_documents(self) -> list[Data]:
        """Search for documents in the FAISS vector store."""
        path = self.get_persist_directory()
        index_path = path / f"{self.index_name}.faiss"

        if not index_path.exists():
            vector_store = self.build_vector_store()
        else:
            vector_store = FAISS.load_local(
                folder_path=str(path),
                embeddings=self.embedding,
                index_name=self.index_name,
                allow_dangerous_deserialization=self.allow_dangerous_deserialization,
            )

        if not vector_store:
            msg = "Failed to load the FAISS index."
            raise ValueError(msg)

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            docs = vector_store.similarity_search(
                query=self.search_query,
                k=self.number_of_results,
            )
            return docs_to_data(docs)
        return []
