import i18n
# from lfx.field_typing import Data

# TODO: remove ignore once the google package is published with types
from google.ai.generativelanguage_v1beta.types import BatchEmbedContentsRequest
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai._common import GoogleGenerativeAIError

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger

MIN_DIMENSION = 1
MAX_DIMENSION = 768


class GoogleGenerativeAIEmbeddingsComponent(Component):
    display_name = "Google Generative AI Embeddings"
    description = i18n.t(
        'components.google.google_generative_ai_embeddings.description')
    documentation: str = "https://python.langchain.com/v0.2/docs/integrations/text_embedding/google_generative_ai/"
    icon = "GoogleGenerativeAI"
    name = "Google Generative AI Embeddings"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.google.google_generative_ai_embeddings.api_key.display_name'),
            required=True
        ),
        MessageTextInput(
            name="model_name",
            display_name=i18n.t(
                'components.google.google_generative_ai_embeddings.model_name.display_name'),
            value="models/text-embedding-004",
            info=i18n.t(
                'components.google.google_generative_ai_embeddings.model_name.info')
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.google.google_generative_ai_embeddings.outputs.embeddings.display_name'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        """Build Google Generative AI Embeddings instance.

        Returns:
            Embeddings: Configured embeddings instance.

        Raises:
            ValueError: If API key is missing.
        """
        if not self.api_key:
            error_msg = i18n.t(
                'components.google.google_generative_ai_embeddings.errors.api_key_required')
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(i18n.t('components.google.google_generative_ai_embeddings.logs.building_embeddings',
                           model=self.model_name))

        class HotaGoogleGenerativeAIEmbeddings(GoogleGenerativeAIEmbeddings):
            def __init__(self, *args, **kwargs) -> None:
                super(GoogleGenerativeAIEmbeddings,
                      self).__init__(*args, **kwargs)

            def embed_documents(
                self,
                texts: list[str],
                *,
                batch_size: int = 100,
                task_type: str | None = None,
                titles: list[str] | None = None,
                output_dimensionality: int | None = 768,
            ) -> list[list[float]]:
                """Embed a list of strings.

                Google Generative AI currently sets a max batch size of 100 strings.

                Args:
                    texts: List[str] The list of strings to embed.
                    batch_size: [int] The batch size of embeddings to send to the model
                    task_type: task_type (https://ai.google.dev/api/rest/v1/TaskType)
                    titles: An optional list of titles for texts provided.
                    Only applicable when TaskType is RETRIEVAL_DOCUMENT.
                    output_dimensionality: Optional reduced dimension for the output embedding.
                    https://ai.google.dev/api/rest/v1/models/batchEmbedContents#EmbedContentRequest

                Returns:
                    List of embeddings, one for each text.

                Raises:
                    ValueError: If output_dimensionality is out of valid range.
                    GoogleGenerativeAIError: If API call fails.
                """
                if output_dimensionality is not None and output_dimensionality < MIN_DIMENSION:
                    error_msg = i18n.t(
                        'components.google.google_generative_ai_embeddings.errors.min_dimension')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                if output_dimensionality is not None and output_dimensionality > MAX_DIMENSION:
                    error_msg = i18n.t('components.google.google_generative_ai_embeddings.errors.max_dimension',
                                       max=MAX_DIMENSION)
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug(i18n.t('components.google.google_generative_ai_embeddings.logs.embedding_documents',
                                    count=len(texts),
                                    batch_size=batch_size,
                                    dimensionality=output_dimensionality or 'default'))

                embeddings: list[list[float]] = []
                batch_start_index = 0
                batch_count = 0

                for batch in GoogleGenerativeAIEmbeddings._prepare_batches(texts, batch_size):
                    batch_count += 1
                    logger.debug(i18n.t('components.google.google_generative_ai_embeddings.logs.processing_batch',
                                        batch_num=batch_count,
                                        batch_size=len(batch)))

                    if titles:
                        titles_batch = titles[batch_start_index:
                                              batch_start_index + len(batch)]
                        batch_start_index += len(batch)
                    else:
                        # type: ignore[list-item]
                        titles_batch = [None] * len(batch)

                    requests = [
                        self._prepare_request(
                            text=text,
                            task_type=task_type,
                            title=title,
                            output_dimensionality=output_dimensionality,
                        )
                        for text, title in zip(batch, titles_batch, strict=True)
                    ]

                    try:
                        result = self.client.batch_embed_contents(
                            BatchEmbedContentsRequest(
                                requests=requests, model=self.model)
                        )
                        embeddings.extend([list(e.values)
                                          for e in result.embeddings])
                        logger.debug(i18n.t('components.google.google_generative_ai_embeddings.logs.batch_completed',
                                            batch_num=batch_count,
                                            embeddings_count=len(result.embeddings)))
                    except Exception as e:
                        error_msg = i18n.t('components.google.google_generative_ai_embeddings.errors.embedding_failed',
                                           error=str(e))
                        logger.exception(error_msg)
                        raise GoogleGenerativeAIError(error_msg) from e

                logger.info(i18n.t('components.google.google_generative_ai_embeddings.logs.documents_embedded',
                                   total=len(embeddings)))
                return embeddings

            def embed_query(
                self,
                text: str,
                task_type: str | None = None,
                title: str | None = None,
                output_dimensionality: int | None = 768,
            ) -> list[float]:
                """Embed a text.

                Args:
                    text: The text to embed.
                    task_type: task_type (https://ai.google.dev/api/rest/v1/TaskType)
                    title: An optional title for the text.
                    Only applicable when TaskType is RETRIEVAL_DOCUMENT.
                    output_dimensionality: Optional reduced dimension for the output embedding.
                    https://ai.google.dev/api/rest/v1/models/batchEmbedContents#EmbedContentRequest

                Returns:
                    Embedding for the text.

                Raises:
                    ValueError: If output_dimensionality is out of valid range.
                """
                if output_dimensionality is not None and output_dimensionality < MIN_DIMENSION:
                    error_msg = i18n.t(
                        'components.google.google_generative_ai_embeddings.errors.min_dimension')
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                if output_dimensionality is not None and output_dimensionality > MAX_DIMENSION:
                    error_msg = i18n.t('components.google.google_generative_ai_embeddings.errors.max_dimension',
                                       max=MAX_DIMENSION)
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                logger.debug(i18n.t('components.google.google_generative_ai_embeddings.logs.embedding_query',
                                    text_length=len(text),
                                    dimensionality=output_dimensionality or 'default'))

                task_type = task_type or "RETRIEVAL_QUERY"
                result = self.embed_documents(
                    [text],
                    task_type=task_type,
                    titles=[title] if title else None,
                    output_dimensionality=output_dimensionality,
                )[0]

                logger.debug(i18n.t('components.google.google_generative_ai_embeddings.logs.query_embedded',
                                    dimension=len(result)))
                return result

        embeddings_instance = HotaGoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=self.api_key
        )

        logger.info(i18n.t(
            'components.google.google_generative_ai_embeddings.logs.embeddings_built'))
        self.status = i18n.t('components.google.google_generative_ai_embeddings.logs.ready',
                             model=self.model_name)

        return embeddings_instance
