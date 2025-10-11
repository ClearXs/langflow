import os
import i18n
from langchain_openai import AzureOpenAIEmbeddings

from lfx.base.models.model import LCModelComponent
from lfx.base.models.openai_constants import OPENAI_EMBEDDING_MODEL_NAMES
from lfx.field_typing import Embeddings
from lfx.io import DropdownInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger


class AzureOpenAIEmbeddingsComponent(LCModelComponent):
    display_name: str = i18n.t(
        'components.azure.azure_openai_embeddings.display_name')
    description: str = i18n.t(
        'components.azure.azure_openai_embeddings.description')
    documentation: str = "https://python.langchain.com/docs/integrations/text_embedding/azureopenai"
    icon = "Azure"
    name = "AzureOpenAIEmbeddings"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    API_VERSION_OPTIONS = [
        "2022-12-01",
        "2023-03-15-preview",
        "2023-05-15",
        "2023-06-01-preview",
        "2023-07-01-preview",
        "2023-08-01-preview",
        "2023-09-01-preview",
        "2023-12-01-preview",
        "2024-02-01",
        "2024-03-01-preview",
        "2024-04-01-preview",
        "2024-05-01-preview",
    ]

    inputs = [
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.azure.azure_openai_embeddings.model.display_name'),
            advanced=False,
            options=OPENAI_EMBEDDING_MODEL_NAMES,
            value=OPENAI_EMBEDDING_MODEL_NAMES[0],
            info=i18n.t('components.azure.azure_openai_embeddings.model.info'),
        ),
        MessageTextInput(
            name="azure_endpoint",
            display_name=i18n.t(
                'components.azure.azure_openai_embeddings.azure_endpoint.display_name'),
            required=True,
            info=i18n.t(
                'components.azure.azure_openai_embeddings.azure_endpoint.info'),
        ),
        MessageTextInput(
            name="azure_deployment",
            display_name=i18n.t(
                'components.azure.azure_openai_embeddings.azure_deployment.display_name'),
            required=True,
            info=i18n.t(
                'components.azure.azure_openai_embeddings.azure_deployment.info'),
        ),
        DropdownInput(
            name="api_version",
            display_name=i18n.t(
                'components.azure.azure_openai_embeddings.api_version.display_name'),
            options=API_VERSION_OPTIONS,
            value=API_VERSION_OPTIONS[-1],
            advanced=True,
            info=i18n.t(
                'components.azure.azure_openai_embeddings.api_version.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.azure.azure_openai_embeddings.api_key.display_name'),
            required=True,
            info=i18n.t(
                'components.azure.azure_openai_embeddings.api_key.info'),
        ),
        IntInput(
            name="dimensions",
            display_name=i18n.t(
                'components.azure.azure_openai_embeddings.dimensions.display_name'),
            info=i18n.t(
                'components.azure.azure_openai_embeddings.dimensions.info'),
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.azure.azure_openai_embeddings.outputs.embeddings.display_name'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        """Build Azure OpenAI embeddings."""
        try:
            self.status = i18n.t('components.azure.azure_openai_embeddings.status.initializing',
                                 model=self.model)

            logger.debug(i18n.t('components.azure.azure_openai_embeddings.logs.building_embeddings',
                                model=self.model,
                                endpoint=self.azure_endpoint,
                                deployment=self.azure_deployment,
                                api_version=self.api_version))

            embeddings = AzureOpenAIEmbeddings(
                model=self.model,
                azure_endpoint=self.azure_endpoint,
                azure_deployment=self.azure_deployment,
                api_version=self.api_version,
                api_key=self.api_key,
                dimensions=self.dimensions or None,
            )

            success_msg = i18n.t('components.azure.azure_openai_embeddings.success.embeddings_initialized',
                                 model=self.model)
            logger.info(success_msg)
            self.status = success_msg

            return embeddings

        except Exception as e:
            error_msg = i18n.t('components.azure.azure_openai_embeddings.errors.connection_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
