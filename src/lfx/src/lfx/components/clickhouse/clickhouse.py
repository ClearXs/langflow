import i18n
from langchain_community.vectorstores import Clickhouse, ClickhouseSettings

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.inputs.inputs import BoolInput, FloatInput
from lfx.io import (
    DictInput,
    DropdownInput,
    HandleInput,
    IntInput,
    SecretStrInput,
    StrInput,
)
from lfx.log.logger import logger
from lfx.schema.data import Data


class ClickhouseVectorStoreComponent(LCVectorStoreComponent):
    display_name = i18n.t('components.clickhouse.clickhouse.display_name')
    description = i18n.t('components.clickhouse.clickhouse.description')
    name = "Clickhouse"
    icon = "Clickhouse"

    inputs = [
        StrInput(
            name="host",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.host.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.host.info'),
            required=True,
            value="localhost"
        ),
        IntInput(
            name="port",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.port.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.port.info'),
            required=True,
            value=8123
        ),
        StrInput(
            name="database",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.database.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.database.info'),
            required=True
        ),
        StrInput(
            name="table",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.table.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.table.info'),
            required=True
        ),
        StrInput(
            name="username",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.username.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.username.info'),
            required=True
        ),
        SecretStrInput(
            name="password",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.password.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.password.info'),
            required=True
        ),
        DropdownInput(
            name="index_type",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.index_type.display_name'),
            options=["annoy", "vector_similarity"],
            info=i18n.t('components.clickhouse.clickhouse.index_type.info'),
            value="annoy",
            advanced=True,
        ),
        DropdownInput(
            name="metric",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.metric.display_name'),
            options=["angular", "euclidean", "manhattan", "hamming", "dot"],
            info=i18n.t('components.clickhouse.clickhouse.metric.info'),
            value="angular",
            advanced=True,
        ),
        BoolInput(
            name="secure",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.secure.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.secure.info'),
            value=False,
            advanced=True,
        ),
        StrInput(
            name="index_param",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.index_param.display_name'),
            info=i18n.t('components.clickhouse.clickhouse.index_param.info'),
            value="100,'L2Distance'",
            advanced=True
        ),
        DictInput(
            name="index_query_params",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.index_query_params.display_name'),
            info=i18n.t(
                'components.clickhouse.clickhouse.index_query_params.info'),
            advanced=True
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.number_of_results.display_name'),
            info=i18n.t(
                'components.clickhouse.clickhouse.number_of_results.info'),
            value=4,
            advanced=True,
        ),
        FloatInput(
            name="score_threshold",
            display_name=i18n.t(
                'components.clickhouse.clickhouse.score_threshold.display_name'),
            info=i18n.t(
                'components.clickhouse.clickhouse.score_threshold.info'),
            advanced=True
        ),
    ]

    @check_cached_vector_store
    def build_vector_store(self) -> Clickhouse:
        try:
            import clickhouse_connect
            logger.debug(
                i18n.t('components.clickhouse.clickhouse.logs.clickhouse_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.clickhouse.clickhouse.errors.clickhouse_not_installed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        # Test connection
        self.status = i18n.t(
            'components.clickhouse.clickhouse.status.connecting')

        try:
            logger.info(i18n.t('components.clickhouse.clickhouse.logs.connecting',
                               host=self.host,
                               port=self.port,
                               database=self.database))

            client = clickhouse_connect.get_client(
                host=self.host, port=self.port, username=self.username, password=self.password
            )
            client.command("SELECT 1")

            logger.info(i18n.t('components.clickhouse.clickhouse.logs.connection_successful',
                               host=self.host))
        except Exception as e:
            error_msg = i18n.t('components.clickhouse.clickhouse.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        # Prepare documents
        self.status = i18n.t(
            'components.clickhouse.clickhouse.status.preparing_documents')

        # Convert DataFrame to Data if needed using parent's method
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        logger.debug(i18n.t('components.clickhouse.clickhouse.logs.document_count',
                            count=len(documents)))

        # Prepare settings
        kwargs = {}
        if self.index_param:
            kwargs["index_param"] = self.index_param.split(",")
            logger.debug(i18n.t('components.clickhouse.clickhouse.logs.index_param_set',
                                params=kwargs["index_param"]))
        if self.index_query_params:
            kwargs["index_query_params"] = self.index_query_params
            logger.debug(i18n.t('components.clickhouse.clickhouse.logs.index_query_params_set',
                                params=self.index_query_params))

        logger.debug(i18n.t('components.clickhouse.clickhouse.logs.settings_configured',
                            table=self.table,
                            database=self.database,
                            index_type=self.index_type,
                            metric=self.metric))

        settings = ClickhouseSettings(
            table=self.table,
            database=self.database,
            host=self.host,
            index_type=self.index_type,
            metric=self.metric,
            password=self.password,
            port=self.port,
            secure=self.secure,
            username=self.username,
            **kwargs,
        )

        # Build vector store
        self.status = i18n.t(
            'components.clickhouse.clickhouse.status.building_store')

        try:
            if documents:
                self.log(i18n.t('components.clickhouse.clickhouse.logs.adding_documents',
                                count=len(documents)))
                logger.info(i18n.t('components.clickhouse.clickhouse.logs.creating_from_documents',
                                   count=len(documents),
                                   table=self.table))

                clickhouse_vs = Clickhouse.from_documents(
                    documents=documents,
                    embedding=self.embedding,
                    config=settings
                )
            else:
                self.log(
                    i18n.t('components.clickhouse.clickhouse.logs.no_documents'))
                logger.info(i18n.t('components.clickhouse.clickhouse.logs.creating_empty_store',
                                   table=self.table))

                clickhouse_vs = Clickhouse(
                    embedding=self.embedding, config=settings)

            success_msg = i18n.t('components.clickhouse.clickhouse.success.store_created',
                                 table=self.table)
            logger.info(success_msg)
            self.status = success_msg

            return clickhouse_vs

        except Exception as e:
            error_msg = i18n.t('components.clickhouse.clickhouse.errors.store_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def search_documents(self) -> list[Data]:
        """Search documents in the vector store."""
        try:
            vector_store = self.build_vector_store()

            self.log(i18n.t('components.clickhouse.clickhouse.logs.search_input',
                            query=self.search_query))
            self.log(i18n.t('components.clickhouse.clickhouse.logs.number_of_results',
                            count=self.number_of_results))

            if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
                self.status = i18n.t(
                    'components.clickhouse.clickhouse.status.searching')

                kwargs = {}
                if self.score_threshold:
                    kwargs["score_threshold"] = self.score_threshold
                    logger.debug(i18n.t('components.clickhouse.clickhouse.logs.score_threshold_set',
                                        threshold=self.score_threshold))

                logger.debug(i18n.t('components.clickhouse.clickhouse.logs.executing_search',
                                    query=self.search_query,
                                    k=self.number_of_results))

                docs = vector_store.similarity_search(
                    query=self.search_query,
                    k=self.number_of_results,
                    **kwargs
                )

                self.log(i18n.t('components.clickhouse.clickhouse.logs.retrieved_documents',
                                count=len(docs)))
                logger.info(i18n.t('components.clickhouse.clickhouse.logs.search_completed',
                                   count=len(docs)))

                data = docs_to_data(docs)
                self.status = data
                return data

            logger.warning(
                i18n.t('components.clickhouse.clickhouse.warnings.empty_query'))
            return []

        except Exception as e:
            error_msg = i18n.t('components.clickhouse.clickhouse.errors.search_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
