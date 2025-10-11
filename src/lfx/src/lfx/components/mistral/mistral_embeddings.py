import os
import i18n
from langchain_mistralai.embeddings import MistralAIEmbeddings
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import Embeddings
from lfx.io import DropdownInput, IntInput, MessageTextInput, Output, SecretStrInput


class MistralAIEmbeddingsComponent(LCModelComponent):
    display_name = i18n.t('components.mistral.mistral_embeddings.display_name')
    description = i18n.t('components.mistral.mistral_embeddings.description')
    icon = "MistralAI"
    name = "MistalAIEmbeddings"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.mistral.mistral_embeddings.model.display_name'),
            advanced=False,
            options=["mistral-embed"],
            value="mistral-embed",
            info=i18n.t('components.mistral.mistral_embeddings.model.info'),
        ),
        SecretStrInput(
            name="mistral_api_key",
            display_name=i18n.t(
                'components.mistral.mistral_embeddings.mistral_api_key.display_name'),
            required=True,
            info=i18n.t(
                'components.mistral.mistral_embeddings.mistral_api_key.info'),
        ),
        IntInput(
            name="max_concurrent_requests",
            display_name=i18n.t(
                'components.mistral.mistral_embeddings.max_concurrent_requests.display_name'),
            advanced=True,
            value=64,
            info=i18n.t(
                'components.mistral.mistral_embeddings.max_concurrent_requests.info'),
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.mistral.mistral_embeddings.max_retries.display_name'),
            advanced=True,
            value=5,
            info=i18n.t(
                'components.mistral.mistral_embeddings.max_retries.info'),
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.mistral.mistral_embeddings.timeout.display_name'),
            advanced=True,
            value=120,
            info=i18n.t('components.mistral.mistral_embeddings.timeout.info'),
        ),
        MessageTextInput(
            name="endpoint",
            display_name=i18n.t(
                'components.mistral.mistral_embeddings.endpoint.display_name'),
            advanced=True,
            value="https://api.mistral.ai/v1/",
            info=i18n.t('components.mistral.mistral_embeddings.endpoint.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.mistral.mistral_embeddings.outputs.embeddings.display_name'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        if not self.mistral_api_key:
            msg = "Mistral API Key is required"
            raise ValueError(msg)

        api_key = SecretStr(self.mistral_api_key).get_secret_value()

        return MistralAIEmbeddings(
            api_key=api_key,
            model=self.model,
            endpoint=self.endpoint,
            max_concurrent_requests=self.max_concurrent_requests,
            max_retries=self.max_retries,
            timeout=self.timeout,
        )
