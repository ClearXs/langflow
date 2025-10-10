import i18n
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import HandleInput, IntInput, SecretStrInput, StrInput
from lfx.schema.data import Data


class SupabaseVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.supabase.supabase.display_name')
    description = i18n.t('components.supabase.supabase.description')
    documentation = "https://python.langchain.com/docs/integrations/vectorstores/supabase"
    name = "SupabaseVectorStore"
    icon = "Supabase"

    inputs = [
        StrInput(
            name="supabase_url",
            display_name=i18n.t(
                'components.supabase.supabase.supabase_url.display_name'),
            required=True
        ),
        SecretStrInput(
            name="supabase_service_key",
            display_name=i18n.t(
                'components.supabase.supabase.supabase_service_key.display_name'),
            required=True
        ),
        StrInput(
            name="table_name",
            display_name=i18n.t(
                'components.supabase.supabase.table_name.display_name'),
            advanced=True
        ),
        StrInput(
            name="query_name",
            display_name=i18n.t(
                'components.supabase.supabase.query_name.display_name')
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.supabase.supabase.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.supabase.supabase.number_of_results.display_name'),
            info=i18n.t('components.supabase.supabase.number_of_results.info'),
            value=4,
            advanced=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> SupabaseVectorStore:
        supabase: Client = create_client(
            self.supabase_url, supabase_key=self.supabase_service_key)

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        if documents:
            supabase_vs = SupabaseVectorStore.from_documents(
                documents=documents,
                embedding=self.embedding,
                query_name=self.query_name,
                client=supabase,
                table_name=self.table_name,
            )
        else:
            supabase_vs = SupabaseVectorStore(
                client=supabase,
                embedding=self.embedding,
                table_name=self.table_name,
                query_name=self.query_name,
            )

        return supabase_vs

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
