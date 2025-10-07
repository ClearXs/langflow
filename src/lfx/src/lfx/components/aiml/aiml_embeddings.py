import i18n
from lfx.base.embeddings.aiml_embeddings import AIMLEmbeddingsImpl
from lfx.base.embeddings.model import LCEmbeddingsModel
from lfx.field_typing import Embeddings
from lfx.inputs.inputs import DropdownInput
from lfx.io import SecretStrInput
from lfx.log.logger import logger


class AIMLEmbeddingsComponent(LCEmbeddingsModel):
    display_name = i18n.t('components.aiml.aiml_embeddings.display_name')
    description = i18n.t('components.aiml.aiml_embeddings.description')
    icon = "AIML"
    name = "AIMLEmbeddings"

    inputs = [
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.aiml.aiml_embeddings.model_name.display_name'),
            options=[
                "text-embedding-3-small",
                "text-embedding-3-large",
                "text-embedding-ada-002",
            ],
            info=i18n.t('components.aiml.aiml_embeddings.model_name.info'),
            required=True,
        ),
        SecretStrInput(
            name="aiml_api_key",
            display_name=i18n.t(
                'components.aiml.aiml_embeddings.aiml_api_key.display_name'),
            info=i18n.t('components.aiml.aiml_embeddings.aiml_api_key.info'),
            value="AIML_API_KEY",
            required=True,
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        """Build and return the AI/ML embeddings model."""
        try:
            # Validate required inputs
            if not self.aiml_api_key:
                error_msg = i18n.t(
                    'components.aiml.aiml_embeddings.errors.api_key_required')
                raise ValueError(error_msg)

            if not self.model_name:
                error_msg = i18n.t(
                    'components.aiml.aiml_embeddings.errors.model_name_required')
                raise ValueError(error_msg)

            self.status = i18n.t('components.aiml.aiml_embeddings.status.initializing_embeddings',
                                 model=self.model_name)

            try:
                embeddings = AIMLEmbeddingsImpl(
                    api_key=self.aiml_api_key,
                    model=self.model_name,
                )

                success_msg = i18n.t('components.aiml.aiml_embeddings.success.embeddings_initialized',
                                     model=self.model_name)
                logger.info(success_msg)
                self.status = success_msg

                return embeddings

            except Exception as e:
                error_msg = i18n.t('components.aiml.aiml_embeddings.errors.embeddings_initialization_failed',
                                   model=self.model_name, error=str(e))
                raise RuntimeError(error_msg) from e

        except (ValueError, RuntimeError) as e:
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.aiml.aiml_embeddings.errors.embeddings_build_failed', error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
