from copy import deepcopy
import os
from typing import TYPE_CHECKING

import i18n
from chromadb.config import Settings
from langchain_chroma import Chroma
from typing_extensions import override

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.base.vectorstores.utils import chroma_collection_to_data
from lfx.inputs.inputs import BoolInput, DropdownInput, HandleInput, IntInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data

if TYPE_CHECKING:
    from lfx.schema.dataframe import DataFrame


class ChromaVectorStoreComponent(LCVectorStoreComponent):
    """Chroma Vector Store with search capabilities."""

    display_name: str = i18n.t('components.chroma.chroma.display_name')
    description: str = i18n.t('components.chroma.chroma.description')
    name = "Chroma"
    icon = "Chroma"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        StrInput(
            name="collection_name",
            display_name=i18n.t(
                'components.chroma.chroma.collection_name.display_name'),
            value="langflow",
            info=i18n.t('components.chroma.chroma.collection_name.info'),
        ),
        StrInput(
            name="persist_directory",
            display_name=i18n.t(
                'components.chroma.chroma.persist_directory.display_name'),
            info=i18n.t('components.chroma.chroma.persist_directory.info'),
        ),
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.chroma.chroma.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        StrInput(
            name="chroma_server_cors_allow_origins",
            display_name=i18n.t(
                'components.chroma.chroma.chroma_server_cors_allow_origins.display_name'),
            info=i18n.t(
                'components.chroma.chroma.chroma_server_cors_allow_origins.info'),
            advanced=True,
        ),
        StrInput(
            name="chroma_server_host",
            display_name=i18n.t(
                'components.chroma.chroma.chroma_server_host.display_name'),
            info=i18n.t('components.chroma.chroma.chroma_server_host.info'),
            advanced=True,
        ),
        IntInput(
            name="chroma_server_http_port",
            display_name=i18n.t(
                'components.chroma.chroma.chroma_server_http_port.display_name'),
            info=i18n.t(
                'components.chroma.chroma.chroma_server_http_port.info'),
            advanced=True,
        ),
        IntInput(
            name="chroma_server_grpc_port",
            display_name=i18n.t(
                'components.chroma.chroma.chroma_server_grpc_port.display_name'),
            info=i18n.t(
                'components.chroma.chroma.chroma_server_grpc_port.info'),
            advanced=True,
        ),
        BoolInput(
            name="chroma_server_ssl_enabled",
            display_name=i18n.t(
                'components.chroma.chroma.chroma_server_ssl_enabled.display_name'),
            info=i18n.t(
                'components.chroma.chroma.chroma_server_ssl_enabled.info'),
            advanced=True,
        ),
        BoolInput(
            name="allow_duplicates",
            display_name=i18n.t(
                'components.chroma.chroma.allow_duplicates.display_name'),
            advanced=True,
            info=i18n.t('components.chroma.chroma.allow_duplicates.info'),
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.chroma.chroma.search_type.display_name'),
            options=["Similarity", "MMR"],
            value="Similarity",
            info=i18n.t('components.chroma.chroma.search_type.info'),
            advanced=True,
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.chroma.chroma.number_of_results.display_name'),
            info=i18n.t('components.chroma.chroma.number_of_results.info'),
            advanced=True,
            value=10,
        ),
        IntInput(
            name="limit",
            display_name=i18n.t('components.chroma.chroma.limit.display_name'),
            advanced=True,
            info=i18n.t('components.chroma.chroma.limit.info'),
        ),
    ]

    @override
    @check_cached_vector_store
    def build_vector_store(self) -> Chroma:
        """Builds the Chroma object."""
        try:
            from chromadb import Client
            from langchain_chroma import Chroma
            logger.debug(
                i18n.t('components.chroma.chroma.logs.chroma_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.chroma.chroma.errors.chroma_not_installed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        self.status = i18n.t('components.chroma.chroma.status.initializing')

        # Chroma settings
        chroma_settings = None
        client = None
        if self.chroma_server_host:
            logger.info(i18n.t('components.chroma.chroma.logs.configuring_server',
                               host=self.chroma_server_host))

            chroma_settings = Settings(
                chroma_server_cors_allow_origins=self.chroma_server_cors_allow_origins or [],
                chroma_server_host=self.chroma_server_host,
                chroma_server_http_port=self.chroma_server_http_port or None,
                chroma_server_grpc_port=self.chroma_server_grpc_port or None,
                chroma_server_ssl_enabled=self.chroma_server_ssl_enabled,
            )
            client = Client(settings=chroma_settings)
            logger.debug(i18n.t('components.chroma.chroma.logs.server_client_created',
                                http_port=self.chroma_server_http_port,
                                grpc_port=self.chroma_server_grpc_port,
                                ssl=self.chroma_server_ssl_enabled))

        # Check persist_directory and expand it if it is a relative path
        persist_directory = self.resolve_path(
            self.persist_directory) if self.persist_directory is not None else None

        if persist_directory:
            logger.info(i18n.t('components.chroma.chroma.logs.using_persist_directory',
                               path=persist_directory))
        else:
            logger.debug(
                i18n.t('components.chroma.chroma.logs.in_memory_mode'))

        try:
            logger.debug(i18n.t('components.chroma.chroma.logs.creating_chroma',
                                collection=self.collection_name))

            chroma = Chroma(
                persist_directory=persist_directory,
                client=client,
                embedding_function=self.embedding,
                collection_name=self.collection_name,
            )

            logger.info(i18n.t('components.chroma.chroma.logs.chroma_created',
                               collection=self.collection_name))

            self._add_documents_to_vector_store(chroma)

            limit = int(self.limit) if self.limit is not None and str(
                self.limit).strip() else None
            self.status = chroma_collection_to_data(chroma.get(limit=limit))

            success_msg = i18n.t('components.chroma.chroma.success.store_created',
                                 collection=self.collection_name)
            logger.info(success_msg)

            return chroma

        except Exception as e:
            error_msg = i18n.t('components.chroma.chroma.errors.store_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _add_documents_to_vector_store(self, vector_store: "Chroma") -> None:
        """Adds documents to the Vector Store."""
        ingest_data: list | Data | DataFrame = self.ingest_data
        if not ingest_data:
            self.status = ""
            logger.debug(
                i18n.t('components.chroma.chroma.logs.no_ingest_data'))
            return

        self.status = i18n.t(
            'components.chroma.chroma.status.preparing_documents')

        # Convert DataFrame to Data if needed using parent's method
        ingest_data = self._prepare_ingest_data()

        logger.debug(i18n.t('components.chroma.chroma.logs.ingest_data_count',
                            count=len(ingest_data) if ingest_data else 0))

        stored_documents_without_id = []
        if self.allow_duplicates:
            stored_data = []
            logger.debug(
                i18n.t('components.chroma.chroma.logs.duplicates_allowed'))
        else:
            limit = int(self.limit) if self.limit is not None and str(
                self.limit).strip() else None
            logger.debug(i18n.t('components.chroma.chroma.logs.checking_duplicates',
                                limit=limit if limit else "unlimited"))

            stored_data = chroma_collection_to_data(
                vector_store.get(limit=limit))
            logger.debug(i18n.t('components.chroma.chroma.logs.existing_documents',
                                count=len(stored_data)))

            for value in deepcopy(stored_data):
                del value.id
                stored_documents_without_id.append(value)

        documents = []
        for _input in ingest_data or []:
            if isinstance(_input, Data):
                if _input not in stored_documents_without_id:
                    documents.append(_input.to_lc_document())
            else:
                error_msg = i18n.t(
                    'components.chroma.chroma.errors.invalid_input_type')
                logger.error(error_msg)
                raise TypeError(error_msg)

        if documents and self.embedding is not None:
            self.log(i18n.t('components.chroma.chroma.logs.adding_documents',
                            count=len(documents)))
            logger.info(i18n.t('components.chroma.chroma.logs.adding_documents_to_store',
                               count=len(documents)))

            # Filter complex metadata to prevent ChromaDB errors
            try:
                from langchain_community.vectorstores.utils import filter_complex_metadata

                filtered_documents = filter_complex_metadata(documents)
                vector_store.add_documents(filtered_documents)
                logger.info(i18n.t('components.chroma.chroma.logs.documents_added_successfully',
                                   count=len(documents)))
            except ImportError:
                warning_msg = i18n.t(
                    'components.chroma.chroma.warnings.filter_not_available')
                self.log(warning_msg)
                logger.warning(warning_msg)
                vector_store.add_documents(documents)
                logger.info(i18n.t('components.chroma.chroma.logs.documents_added_without_filter',
                                   count=len(documents)))
        else:
            self.log(i18n.t('components.chroma.chroma.logs.no_documents'))
            logger.debug(
                i18n.t('components.chroma.chroma.logs.no_documents_to_add'))
