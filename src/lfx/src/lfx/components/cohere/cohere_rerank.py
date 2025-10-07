import i18n
from lfx.base.compressors.model import LCCompressorComponent
from lfx.field_typing import BaseDocumentCompressor
from lfx.inputs.inputs import SecretStrInput
from lfx.io import DropdownInput
from lfx.log.logger import logger
from lfx.template.field.base import Output


class CohereRerankComponent(LCCompressorComponent):
    display_name = i18n.t('components.cohere.cohere_rerank.display_name')
    description = i18n.t('components.cohere.cohere_rerank.description')
    name = "CohereRerank"
    icon = "Cohere"

    inputs = [
        *LCCompressorComponent.inputs,
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.cohere.cohere_rerank.api_key.display_name'),
            info=i18n.t('components.cohere.cohere_rerank.api_key.info'),
        ),
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.cohere.cohere_rerank.model.display_name'),
            options=[
                "rerank-english-v3.0",
                "rerank-multilingual-v3.0",
                "rerank-english-v2.0",
                "rerank-multilingual-v2.0",
            ],
            value="rerank-english-v3.0",
            info=i18n.t('components.cohere.cohere_rerank.model.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.cohere.cohere_rerank.outputs.reranked_documents.display_name'),
            name="reranked_documents",
            method="compress_documents",
        ),
    ]

    # type: ignore[type-var]
    def build_compressor(self) -> BaseDocumentCompressor:
        try:
            from langchain_cohere import CohereRerank
            logger.debug(
                i18n.t('components.cohere.cohere_rerank.logs.cohere_imported'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.cohere.cohere_rerank.errors.cohere_not_installed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            self.status = i18n.t(
                'components.cohere.cohere_rerank.status.initializing')
            logger.info(i18n.t('components.cohere.cohere_rerank.logs.initializing',
                               model=self.model,
                               top_n=self.top_n))

            compressor = CohereRerank(
                cohere_api_key=self.api_key,
                model=self.model,
                top_n=self.top_n,
            )

            success_msg = i18n.t('components.cohere.cohere_rerank.success.compressor_created',
                                 model=self.model,
                                 top_n=self.top_n)
            self.status = success_msg
            logger.info(success_msg)

            return compressor

        except Exception as e:
            error_msg = i18n.t('components.cohere.cohere_rerank.errors.creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
