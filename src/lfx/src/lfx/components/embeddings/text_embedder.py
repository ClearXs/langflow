import os
import i18n
from typing import TYPE_CHECKING

from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, MessageInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data

if TYPE_CHECKING:
    from lfx.field_typing import Embeddings
    from lfx.schema.message import Message


class TextEmbedderComponent(Component):
    display_name: str = i18n.t(
        'components.embeddings.text_embedder.display_name')
    description: str = i18n.t(
        'components.embeddings.text_embedder.description')
    icon = "binary"
    legacy: bool = True
    replacement = ["models.EmbeddingModel"]

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        HandleInput(
            name="embedding_model",
            display_name=i18n.t(
                'components.embeddings.text_embedder.embedding_model.display_name'),
            info=i18n.t(
                'components.embeddings.text_embedder.embedding_model.info'),
            input_types=["Embeddings"],
            required=True,
        ),
        MessageInput(
            name="message",
            display_name=i18n.t(
                'components.embeddings.text_embedder.message.display_name'),
            info=i18n.t('components.embeddings.text_embedder.message.info'),
            required=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.embeddings.text_embedder.outputs.embeddings.display_name'),
            name="embeddings",
            method="generate_embeddings"
        ),
    ]

    def generate_embeddings(self) -> Data:
        """Generate embeddings for a given message using the specified embedding model.

        Returns:
            Data: Data object containing the text and its embedding vector.

        Raises:
            ValueError: If the embedding model is invalid or message is empty.
        """
        try:
            embedding_model: Embeddings = self.embedding_model
            message: Message = self.message

            logger.info(
                i18n.t('components.embeddings.text_embedder.logs.starting_generation'))

            # Validate embedding model
            if not embedding_model or not hasattr(embedding_model, "embed_documents"):
                error_msg = i18n.t(
                    'components.embeddings.text_embedder.errors.invalid_model')
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Extract text content from message
            text_content = message.text if message and message.text else ""
            if not text_content:
                error_msg = i18n.t(
                    'components.embeddings.text_embedder.errors.no_text_content')
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.debug(i18n.t('components.embeddings.text_embedder.logs.text_extracted',
                                length=len(text_content)))

            # Generate embeddings
            logger.debug(
                i18n.t('components.embeddings.text_embedder.logs.generating_embeddings'))
            embeddings = embedding_model.embed_documents([text_content])

            if not embeddings or not isinstance(embeddings, list):
                error_msg = i18n.t(
                    'components.embeddings.text_embedder.errors.invalid_embeddings')
                logger.error(error_msg)
                raise ValueError(error_msg)

            embedding_vector = embeddings[0]

            logger.info(i18n.t('components.embeddings.text_embedder.logs.embeddings_generated',
                               dimension=len(embedding_vector)))

            # Create result data
            result_data = Data(
                data={"text": text_content, "embeddings": embedding_vector})
            self.status = {"text": text_content,
                           "embeddings": embedding_vector}

            logger.info(
                i18n.t('components.embeddings.text_embedder.logs.generation_completed'))
            return result_data

        except ValueError:
            # Re-raise ValueError with already translated message
            raise
        except Exception as e:
            error_msg = i18n.t('components.embeddings.text_embedder.errors.generation_failed',
                               error=str(e))
            logger.exception(error_msg)

            error_data = Data(
                data={"text": "", "embeddings": [], "error": str(e)})
            self.status = {"error": str(e)}
            return error_data
