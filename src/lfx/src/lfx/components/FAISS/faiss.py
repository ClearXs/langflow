import i18n
from pathlib import Path

from langchain_community.vectorstores import FAISS

from lfx.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from lfx.helpers.data import docs_to_data
from lfx.io import BoolInput, HandleInput, IntInput, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class FaissVectorStoreComponent(LCVectorStoreComponent):
    """FAISS Vector Store with search capabilities."""

    display_name: str = "FAISS"
    description: str = i18n.t('components.faiss.faiss.description')
    name = "FAISS"
    icon = "FAISS"

    inputs = [
        StrInput(
            name="index_name",
            display_name=i18n.t(
                'components.faiss.faiss.index_name.display_name'),
            value="langflow_index",
            info=i18n.t('components.faiss.faiss.index_name.info'),
        ),
        StrInput(
            name="persist_directory",
            display_name=i18n.t(
                'components.faiss.faiss.persist_directory.display_name'),
            info=i18n.t('components.faiss.faiss.persist_directory.info'),
        ),
        *LCVectorStoreComponent.inputs,
        BoolInput(
            name="allow_dangerous_deserialization",
            display_name=i18n.t(
                'components.faiss.faiss.allow_dangerous_deserialization.display_name'),
            info=i18n.t(
                'components.faiss.faiss.allow_dangerous_deserialization.info'),
            advanced=True,
            value=True,
        ),
        HandleInput(
            name="embedding",
            display_name=i18n.t(
                'components.faiss.faiss.embedding.display_name'),
            input_types=["Embeddings"]
        ),
        IntInput(
            name="number_of_results",
            display_name=i18n.t(
                'components.faiss.faiss.number_of_results.display_name'),
            info=i18n.t('components.faiss.faiss.number_of_results.info'),
            advanced=True,
            value=4,
        ),
    ]

    @staticmethod
    def resolve_path(path: str) -> str:
        """Resolve the path relative to the Langflow root.

        Args:
            path: The path to resolve.

        Returns:
            str: The resolved path as a string.
        """
        resolved = str(Path(path).resolve())
        logger.debug(i18n.t('components.faiss.faiss.logs.path_resolved',
                            original=path,
                            resolved=resolved))
        return resolved

    def get_persist_directory(self) -> Path:
        """Returns the resolved persist directory path or the current directory if not set.

        Returns:
            Path: The persist directory path.
        """
        if self.persist_directory:
            path = Path(self.resolve_path(self.persist_directory))
            logger.debug(i18n.t('components.faiss.faiss.logs.using_persist_directory',
                                path=str(path)))
            return path

        logger.debug(
            i18n.t('components.faiss.faiss.logs.using_current_directory'))
        return Path()

    @check_cached_vector_store
    def build_vector_store(self) -> FAISS:
        """Builds the FAISS vector store object.

        Returns:
            FAISS: The constructed FAISS vector store.

        Raises:
            ValueError: If document conversion or index creation fails.
        """
        logger.info(i18n.t('components.faiss.faiss.logs.building_vector_store'))

        path = self.get_persist_directory()

        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(i18n.t('components.faiss.faiss.logs.directory_created',
                                path=str(path)))
        except Exception as e:
            error_msg = i18n.t('components.faiss.faiss.errors.directory_creation_failed',
                               path=str(path),
                               error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        # Convert DataFrame to Data if needed using parent's method
        logger.debug(i18n.t('components.faiss.faiss.logs.preparing_data'))
        self.ingest_data = self._prepare_ingest_data()

        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                documents.append(_input)

        if not documents:
            warning_msg = i18n.t('components.faiss.faiss.logs.no_documents')
            logger.warning(warning_msg)
            self.log(warning_msg)

        logger.info(i18n.t('components.faiss.faiss.logs.creating_index',
                           count=len(documents)))

        try:
            faiss = FAISS.from_documents(
                documents=documents, embedding=self.embedding)
            logger.info(i18n.t('components.faiss.faiss.logs.index_created'))
        except Exception as e:
            error_msg = i18n.t('components.faiss.faiss.errors.index_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        try:
            faiss.save_local(str(path), self.index_name)
            logger.info(i18n.t('components.faiss.faiss.logs.index_saved',
                               path=str(path),
                               name=self.index_name))
        except Exception as e:
            error_msg = i18n.t('components.faiss.faiss.errors.index_save_failed',
                               error=str(e))
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        return faiss

    def search_documents(self) -> list[Data]:
        """Search for documents in the FAISS vector store.

        Returns:
            list[Data]: List of search results.

        Raises:
            ValueError: If index loading or search fails.
        """
        logger.info(i18n.t('components.faiss.faiss.logs.starting_search'))

        path = self.get_persist_directory()
        index_path = path / f"{self.index_name}.faiss"

        if not index_path.exists():
            logger.info(i18n.t('components.faiss.faiss.logs.index_not_found',
                               path=str(index_path)))
            vector_store = self.build_vector_store()
        else:
            logger.info(i18n.t('components.faiss.faiss.logs.loading_index',
                               path=str(index_path)))
            try:
                vector_store = FAISS.load_local(
                    folder_path=str(path),
                    embeddings=self.embedding,
                    index_name=self.index_name,
                    allow_dangerous_deserialization=self.allow_dangerous_deserialization,
                )
                logger.info(i18n.t('components.faiss.faiss.logs.index_loaded'))
            except Exception as e:
                error_msg = i18n.t('components.faiss.faiss.errors.index_load_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

        if not vector_store:
            error_msg = i18n.t('components.faiss.faiss.errors.failed_to_load')
            logger.error(error_msg)
            raise ValueError(error_msg)

        if self.search_query and isinstance(self.search_query, str) and self.search_query.strip():
            logger.debug(i18n.t('components.faiss.faiss.logs.searching_with_query',
                                query=self.search_query[:100] + ("..." if len(self.search_query) > 100 else "")))

            try:
                docs = vector_store.similarity_search(
                    query=self.search_query,
                    k=self.number_of_results,
                )
                logger.info(i18n.t('components.faiss.faiss.logs.search_completed',
                                   count=len(docs)))
                return docs_to_data(docs)
            except Exception as e:
                error_msg = i18n.t('components.faiss.faiss.errors.search_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

        logger.info(i18n.t('components.faiss.faiss.logs.no_query'))
        return []
