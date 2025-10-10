import os
import i18n
from lfx.custom import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema import Data


class ChunkDoclingDocument(Component):
    display_name = i18n.t(
        'components.docling.chunk_docling_document.display_name')
    description = i18n.t(
        'components.docling.chunk_docling_document.description')
    icon = "Docling"
    name = "ChunkDoclingDocument"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        DataInput(
            name="data",
            display_name=i18n.t(
                'components.docling.chunk_docling_document.data.display_name'),
            info=i18n.t('components.docling.chunk_docling_document.data.info'),
            is_list=True,
        ),
        MessageTextInput(
            name="tokenizer",
            display_name=i18n.t(
                'components.docling.chunk_docling_document.tokenizer.display_name'),
            info=i18n.t(
                'components.docling.chunk_docling_document.tokenizer.info'),
            value="nltk",
            advanced=True,
        ),
        MessageTextInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.docling.chunk_docling_document.max_tokens.display_name'),
            info=i18n.t(
                'components.docling.chunk_docling_document.max_tokens.info'),
            value="512",
        ),
    ]

    outputs = [
        Output(display_name=i18n.t('components.docling.chunk_docling_document.outputs.chunks.display_name'),
               name="chunks",
               method="chunk_document"),
    ]

    def chunk_document(self) -> list[Data]:
        """Chunk a Docling document into smaller pieces.

        Returns:
            list[Data]: List of chunked document data.

        Raises:
            ImportError: If docling or docling_core is not installed.
            ValueError: If chunking fails.
        """
        try:
            from docling.chunking import HybridChunker
            from docling_core.types.doc import DoclingDocument, DocumentOrigin
            logger.debug(i18n.t(
                'components.docling.chunk_docling_document.logs.docling_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.docling.chunk_docling_document.errors.docling_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        if not self.data:
            logger.warning(
                i18n.t('components.docling.chunk_docling_document.logs.no_data'))
            return []

        try:
            logger.info(i18n.t('components.docling.chunk_docling_document.logs.processing_documents',
                               count=len(self.data)))
            self.status = i18n.t(
                'components.docling.chunk_docling_document.status.processing')

            max_tokens = int(self.max_tokens)
            logger.debug(i18n.t('components.docling.chunk_docling_document.logs.chunker_config',
                                tokenizer=self.tokenizer,
                                max_tokens=max_tokens))

            chunker = HybridChunker(
                tokenizer=self.tokenizer, max_tokens=max_tokens)
            all_chunks = []

            for idx, data_item in enumerate(self.data, 1):
                logger.info(i18n.t('components.docling.chunk_docling_document.logs.processing_document',
                                   index=idx,
                                   total=len(self.data)))

                # Get document JSON
                doc_json = data_item.data.get("json")
                if not doc_json:
                    logger.warning(i18n.t('components.docling.chunk_docling_document.logs.no_json',
                                          index=idx))
                    continue

                # Create DoclingDocument
                try:
                    docling_doc = DoclingDocument.model_validate(doc_json)
                    logger.debug(i18n.t('components.docling.chunk_docling_document.logs.document_validated',
                                        index=idx))
                except Exception as e:
                    logger.error(i18n.t('components.docling.chunk_docling_document.errors.validation_failed',
                                        index=idx,
                                        error=str(e)))
                    continue

                # Chunk the document
                try:
                    chunks = list(chunker.chunk(dl_doc=docling_doc))
                    logger.info(i18n.t('components.docling.chunk_docling_document.logs.chunks_created',
                                       index=idx,
                                       chunk_count=len(chunks)))

                    # Convert chunks to Data objects
                    for chunk_idx, chunk in enumerate(chunks, 1):
                        chunk_data = Data(
                            text=chunk.text,
                            data={
                                "chunk_index": chunk_idx,
                                "document_index": idx,
                                "meta": chunk.meta.model_dump() if hasattr(chunk, 'meta') else {},
                                "original_document": data_item.data,
                            },
                        )
                        all_chunks.append(chunk_data)
                        logger.debug(i18n.t('components.docling.chunk_docling_document.logs.chunk_added',
                                            chunk_index=chunk_idx,
                                            text_length=len(chunk.text)))

                except Exception as e:
                    logger.error(i18n.t('components.docling.chunk_docling_document.errors.chunking_failed',
                                        index=idx,
                                        error=str(e)))
                    continue

            total_chunks = len(all_chunks)
            success_msg = i18n.t('components.docling.chunk_docling_document.status.completed',
                                 total_chunks=total_chunks,
                                 total_docs=len(self.data))
            self.status = success_msg
            logger.info(success_msg)

            return all_chunks

        except ValueError as e:
            error_msg = i18n.t('components.docling.chunk_docling_document.errors.invalid_max_tokens',
                               error=str(e))
            logger.error(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = i18n.t('components.docling.chunk_docling_document.errors.chunking_process_failed',
                               error=str(e))
            logger.exception(error_msg)
            self.status = error_msg
            raise ValueError(error_msg) from e
