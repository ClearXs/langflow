import os
import i18n
from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import (
    BoolInput,
    DictInput,
    DropdownInput,
    FloatInput,
    HandleInput,
    IntInput,
    SecretStrInput,
    StrInput,
)
from lfx.schema.data import Data


class MilvusVectorStoreComponent(LCVectorStoreComponent):
    """Milvus vector store with search capabilities."""

    display_name: str = i18n.t('components.milvus.milvus.display_name')
    description: str = i18n.t('components.milvus.milvus.description')
    name = "Milvus"
    icon = "Milvus"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.milvus.milvus.collection_name.display_name'),
            value="langflow",
            info=i18n.t('components.milvus.milvus.collection_name.info'),
        ),
        StrInput(
            name="collection_description",
            display_name=i18n.t(
                'components.milvus.milvus.collection_description.display_name'),
            value="",
            info=i18n.t(
                'components.milvus.milvus.collection_description.info'),
        ),
        StrInput(
            name="uri",
            display_name=i18n.t('components.milvus.milvus.uri.display_name'),
            value="http://localhost:19530",
            info=i18n.t('components.milvus.milvus.uri.info'),
        ),
        SecretStrInput(
            name="password",
            display_name=i18n.t(
                'components.milvus.milvus.password.display_name'),
            value="",
            info=i18n.t('components.milvus.milvus.password.info'),
        ),
        DictInput(
            name="connection_args",
            display_name=i18n.t(
                'components.milvus.milvus.connection_args.display_name'),
            advanced=True,
            info=i18n.t('components.milvus.milvus.connection_args.info'),
        ),
        StrInput(
            name="primary_field",
            display_name=i18n.t(
                'components.milvus.milvus.primary_field.display_name'),
            value="pk",
            info=i18n.t('components.milvus.milvus.primary_field.info'),
        ),
        StrInput(
            name="text_field",
            display_name=i18n.t(
                'components.milvus.milvus.text_field.display_name'),
            value="text",
            info=i18n.t('components.milvus.milvus.text_field.info'),
        ),
        StrInput(
            name="vector_field",
            display_name=i18n.t(
                'components.milvus.milvus.vector_field.display_name'),
            value="vector",
            info=i18n.t('components.milvus.milvus.vector_field.info'),
        ),
        DropdownInput(
            name="consistency_level",
            display_name=i18n.t(
                'components.milvus.milvus.consistency_level.display_name'),
            options=["Bounded", "Session", "Strong", "Eventual"],
            value="Session",
            advanced=True,
            info=i18n.t('components.milvus.milvus.consistency_level.info'),
        ),
        DictInput(
            name="index_params",
            display_name=i18n.t(
                'components.milvus.milvus.index_params.display_name'),
            advanced=True,
            info=i18n.t('components.milvus.milvus.index_params.info'),
        ),
        DictInput(
            name="search_params",
            display_name=i18n.t(
                'components.milvus.milvus.search_params.display_name'),
            advanced=True,
            info=i18n.t('components.milvus.milvus.search_params.info'),
        ),
        BoolInput(
            name="drop_old",
            display_name=i18n.t(
                'components.milvus.milvus.drop_old.display_name'),
            value=False,
            advanced=True,
            info=i18n.t('components.milvus.milvus.drop_old.info'),
        ),
        FloatInput(
            name="timeout",
            display_name=i18n.t(
                'components.milvus.milvus.timeout.display_name'),
            advanced=True,
            info=i18n.t('components.milvus.milvus.timeout.info'),
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.milvus.milvus.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.milvus.milvus.number_of_results.display_name'),
            info=i18n.t('components.milvus.milvus.number_of_results.info'),
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self):
        try:
            from langchain_milvus.vectorstores import Milvus as LangchainMilvus
        except ImportError as e:
            msg = "Could not import Milvus integration package. Please install it with `pip install langchain-milvus`."
            raise ImportError(msg) from e
        self.connection_args.update(uri=self.uri, token=self.password)
        milvus_store = LangchainMilvus(
            embedding_function=self.embedding,
            collection_name=self.collection_name,
            collection_description=self.collection_description,
            connection_args=self.connection_args,
            consistency_level=self.consistency_level,
            index_params=self.index_params,
            search_params=self.search_params,
            drop_old=self.drop_old,
            auto_id=True,
            primary_field=self.primary_field,
            text_field=self.text_field,
            vector_field=self.vector_field,
            timeout=self.timeout,
        )

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        if documents:
            milvus_store.add_documents(documents)

        return milvus_store

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
