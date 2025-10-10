import i18n
from uuid import UUID

from langchain_community.graph_vectorstores import CassandraGraphVectorStore

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import DictInput, FloatInput
from lfx.io import (
    DropdownInput,
    HandleInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
)
from lfx.schema.data import Data


class CassandraGraphVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t(
        'components.vectorstores.cassandra_graph.display_name')
    description = i18n.t('components.vectorstores.cassandra_graph.description')
    name = "CassandraGraph"
    icon = "Cassandra"

    inputs = [
        MessageTextInput(
            name="database_ref",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.database_ref.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.database_ref.info'),
            required=True,
        ),
        MessageTextInput(
            name="username",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.username.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.username.info')
        ),
        SecretStrInput(
            name="token",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.token.display_name'),
            info=i18n.t('components.vectorstores.cassandra_graph.token.info'),
            required=True,
        ),
        MessageTextInput(
            name="keyspace",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.keyspace.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.keyspace.info'),
            required=True,
        ),
        MessageTextInput(
            name="table_name",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.table_name.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.table_name.info'),
            required=True,
        ),
        DropdownInput(
            name="setup_mode",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.setup_mode.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.setup_mode.info'),
            options=["Sync", "Off"],
            value="Sync",
            advanced=True,
        ),
        DictInput(
            name="cluster_kwargs",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.cluster_kwargs.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.cluster_kwargs.info'),
            advanced=True,
            list=True,
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.number_of_results.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.number_of_results.info'),
            value=4,
            advanced=True,
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.search_type.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.search_type.info'),
            options=[
                "Traversal",
                "MMR traversal",
                "Similarity",
                "Similarity with score threshold",
                "MMR (Max Marginal Relevance)",
            ],
            value="Traversal",
            advanced=True,
        ),
        IntInput(
            name="depth",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.depth.display_name'),
            info=i18n.t('components.vectorstores.cassandra_graph.depth.info'),
            value=1,
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.search_score_threshold.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.search_score_threshold.info'),
            value=0,
            advanced=True,
        ),
        DictInput(
            name="search_filter",
            display_name=i18n.t(
                'components.vectorstores.cassandra_graph.search_filter.display_name'),
            info=i18n.t(
                'components.vectorstores.cassandra_graph.search_filter.info'),
            advanced=True,
            list=True,
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> CassandraGraphVectorStore:
        try:
            import cassio
            from langchain_community.utilities.cassandra import SetupMode
        except ImportError as e:
            msg = "Could not import cassio integration package. Please install it with `pip install cassio`."
            raise ImportError(msg) from e

        database_ref = self.database_ref

        try:
            UUID(self.database_ref)
            is_astra = True
        except ValueError:
            is_astra = False
            if "," in self.database_ref:
                # use a copy because we can't change the type of the parameter
                database_ref = self.database_ref.split(",")

        if is_astra:
            cassio.init(
                database_id=database_ref,
                token=self.token,
                cluster_kwargs=self.cluster_kwargs,
            )
        else:
            cassio.init(
                contact_points=database_ref,
                username=self.username,
                password=self.token,
                cluster_kwargs=self.cluster_kwargs,
            )

        self.ingest_data = self._prepare_ingest_data()

        documents = []

        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        setup_mode = SetupMode.OFF if self.setup_mode == "Off" else SetupMode.SYNC

        if documents:
            self.log(f"Adding {len(documents)} documents to the Vector Store.")
            store = CassandraGraphVectorStore.from_documents(
                documents=documents,
                embedding=self.embedding,
                node_table=self.table_name,
                keyspace=self.keyspace,
            )
        else:
            self.log("No documents to add to the Vector Store.")
            store = CassandraGraphVectorStore(
                embedding=self.embedding,
                node_table=self.table_name,
                keyspace=self.keyspace,
                setup_mode=setup_mode,
            )
        return store

    def _map_search_type(self) -> str:
        if self.search_type == "Similarity":
            return "similarity"
        if self.search_type == "Similarity with score threshold":
            return "similarity_score_threshold"
        if self.search_type == "MMR (Max Marginal Relevance)":
            return "mmr"
        if self.search_type == "MMR Traversal":
            return "mmr_traversal"
        return "traversal"

    def search_documents(self) -> list[Data]:
        vector_store = self.build_vector_store()

        self.log(f"Search input: {self.search_query}")
        self.log(f"Search type: {self.search_type}")
        self.log(f"Number of results: {self.number_of_results}")

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            try:
                search_type = self._map_search_type()
                search_args = self._build_search_args()

                self.log(f"Search args: {search_args}")

                docs = vector_store.search(
                    query=self.search_query, search_type=search_type, **search_args)
            except KeyError as e:
                if "content" in str(e):
                    msg = (
                        "You should ingest data through Langflow (or LangChain) to query it in Langflow. "
                        "Your collection does not contain a field name 'content'."
                    )
                    raise ValueError(msg) from e
                raise

            self.log(f"Retrieved documents: {len(docs)}")

            data = docs_to_data(docs)
            self.status = data
            return data
        return []

    def _build_search_args(self):
        args = {
            "k": self.number_of_results,
            "score_threshold": self.search_score_threshold,
            "depth": self.depth,
        }

        if self.search_filter:
            clean_filter = {k: v for k,
                            v in self.search_filter.items() if k and v}
            if len(clean_filter) > 0:
                args["filter"] = clean_filter
        return args

    def get_retriever_kwargs(self):
        search_args = self._build_search_args()
        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_args,
        }
