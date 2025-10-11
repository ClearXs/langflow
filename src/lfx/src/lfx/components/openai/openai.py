import os
import i18n
from langchain_openai import OpenAIEmbeddings

from lfx.base.embeddings.model import LCEmbeddingsModel
from lfx.base.models.openai_constants import OPENAI_EMBEDDING_MODEL_NAMES
from lfx.field_typing import Embeddings
from lfx.io import BoolInput, DictInput, DropdownInput, FloatInput, IntInput, MessageTextInput, SecretStrInput


class OpenAIEmbeddingsComponent(LCEmbeddingsModel):
    display_name = i18n.t('components.openai.openai.display_name')
    description = i18n.t('components.openai.openai.description')
    icon = "OpenAI"
    name = "OpenAIEmbeddings"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        DictInput(
            name="default_headers",
            display_name=i18n.t(
                'components.openai.openai.default_headers.display_name'),
            advanced=True,
            info=i18n.t('components.openai.openai.default_headers.info'),
        ),
        DictInput(
            name="default_query",
            display_name=i18n.t(
                'components.openai.openai.default_query.display_name'),
            advanced=True,
            info=i18n.t('components.openai.openai.default_query.info'),
        ),
        IntInput(
            name="chunk_size",
            display_name=i18n.t(
                'components.openai.openai.chunk_size.display_name'),
            advanced=True,
            value=1000
        ),
        MessageTextInput(
            name="client",
            display_name=i18n.t(
                'components.openai.openai.client.display_name'),
            advanced=True
        ),
        MessageTextInput(
            name="deployment",
            display_name=i18n.t(
                'components.openai.openai.deployment.display_name'),
            advanced=True
        ),
        IntInput(
            name="embedding_ctx_length",
            display_name=i18n.t(
                'components.openai.openai.embedding_ctx_length.display_name'),
            advanced=True,
            value=1536
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.openai.openai.max_retries.display_name'),
            value=3,
            advanced=True
        ),
        DropdownInput(
            name="model",
            display_name=i18n.t('components.openai.openai.model.display_name'),
            advanced=False,
            options=OPENAI_EMBEDDING_MODEL_NAMES,
            value="text-embedding-3-small",
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.openai.openai.model_kwargs.display_name'),
            advanced=True
        ),
        SecretStrInput(
            name="openai_api_key",
            display_name=i18n.t(
                'components.openai.openai.openai_api_key.display_name'),
            value="OPENAI_API_KEY",
            required=True
        ),
        MessageTextInput(
            name="openai_api_base",
            display_name=i18n.t(
                'components.openai.openai.openai_api_base.display_name'),
            advanced=True
        ),
        MessageTextInput(
            name="openai_api_type",
            display_name=i18n.t(
                'components.openai.openai.openai_api_type.display_name'),
            advanced=True
        ),
        MessageTextInput(
            name="openai_api_version",
            display_name=i18n.t(
                'components.openai.openai.openai_api_version.display_name'),
            advanced=True
        ),
        MessageTextInput(
            name="openai_organization",
            display_name=i18n.t(
                'components.openai.openai.openai_organization.display_name'),
            advanced=True,
        ),
        MessageTextInput(
            name="openai_proxy",
            display_name=i18n.t(
                'components.openai.openai.openai_proxy.display_name'),
            advanced=True
        ),
        FloatInput(
            name="request_timeout",
            display_name=i18n.t(
                'components.openai.openai.request_timeout.display_name'),
            advanced=True
        ),
        BoolInput(
            name="show_progress_bar",
            display_name=i18n.t(
                'components.openai.openai.show_progress_bar.display_name'),
            advanced=True
        ),
        BoolInput(
            name="skip_empty",
            display_name=i18n.t(
                'components.openai.openai.skip_empty.display_name'),
            advanced=True
        ),
        MessageTextInput(
            name="tiktoken_model_name",
            display_name=i18n.t(
                'components.openai.openai.tiktoken_model_name.display_name'),
            advanced=True,
        ),
        BoolInput(
            name="tiktoken_enable",
            display_name=i18n.t(
                'components.openai.openai.tiktoken_enable.display_name'),
            advanced=True,
            value=True,
            info=i18n.t('components.openai.openai.tiktoken_enable.info'),
        ),
        IntInput(
            name="dimensions",
            display_name=i18n.t(
                'components.openai.openai.dimensions.display_name'),
            info=i18n.t('components.openai.openai.dimensions.info'),
            advanced=True,
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        return OpenAIEmbeddings(
            client=self.client or None,
            model=self.model,
            dimensions=self.dimensions or None,
            deployment=self.deployment or None,
            api_version=self.openai_api_version or None,
            base_url=self.openai_api_base or None,
            openai_api_type=self.openai_api_type or None,
            openai_proxy=self.openai_proxy or None,
            embedding_ctx_length=self.embedding_ctx_length,
            api_key=self.openai_api_key or None,
            organization=self.openai_organization or None,
            allowed_special="all",
            disallowed_special="all",
            chunk_size=self.chunk_size,
            max_retries=self.max_retries,
            timeout=self.request_timeout or None,
            tiktoken_enabled=self.tiktoken_enable,
            tiktoken_model_name=self.tiktoken_model_name or None,
            show_progress_bar=self.show_progress_bar,
            model_kwargs=self.model_kwargs,
            skip_empty=self.skip_empty,
            default_headers=self.default_headers or None,
            default_query=self.default_query or None,
        )
