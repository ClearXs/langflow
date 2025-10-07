from typing import Any
import i18n

from langchain_openai import OpenAIEmbeddings

from lfx.base.embeddings.model import LCEmbeddingsModel
from lfx.base.models.openai_constants import OPENAI_EMBEDDING_MODEL_NAMES
from lfx.field_typing import Embeddings
from lfx.io import (
    BoolInput,
    DictInput,
    DropdownInput,
    FloatInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
)
from lfx.schema.dotdict import dotdict


class EmbeddingModelComponent(LCEmbeddingsModel):
    display_name = i18n.t('components.models.embedding_model.display_name')
    description = i18n.t('components.models.embedding_model.description')
    documentation: str = "https://docs.langflow.org/components-embedding-models"
    icon = "binary"
    name = "EmbeddingModel"
    category = "models"

    inputs = [
        DropdownInput(
            name="provider",
            display_name=i18n.t(
                'components.models.embedding_model.provider.display_name'),
            options=["OpenAI"],
            value="OpenAI",
            info=i18n.t('components.models.embedding_model.provider.info'),
            real_time_refresh=True,
            options_metadata=[{"icon": "OpenAI"}],
        ),
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.models.embedding_model.model.display_name'),
            options=OPENAI_EMBEDDING_MODEL_NAMES,
            value=OPENAI_EMBEDDING_MODEL_NAMES[0],
            info=i18n.t('components.models.embedding_model.model.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.models.embedding_model.api_key.display_name'),
            info=i18n.t('components.models.embedding_model.api_key.info'),
            required=True,
            show=True,
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="api_base",
            display_name=i18n.t(
                'components.models.embedding_model.api_base.display_name'),
            info=i18n.t('components.models.embedding_model.api_base.info'),
            advanced=True,
        ),
        IntInput(
            name="dimensions",
            display_name=i18n.t(
                'components.models.embedding_model.dimensions.display_name'),
            info=i18n.t('components.models.embedding_model.dimensions.info'),
            advanced=True,
        ),
        IntInput(
            name="chunk_size",
            display_name=i18n.t(
                'components.models.embedding_model.chunk_size.display_name'),
            info=i18n.t('components.models.embedding_model.chunk_size.info'),
            advanced=True,
            value=1000
        ),
        FloatInput(
            name="request_timeout",
            display_name=i18n.t(
                'components.models.embedding_model.request_timeout.display_name'),
            info=i18n.t(
                'components.models.embedding_model.request_timeout.info'),
            advanced=True
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.models.embedding_model.max_retries.display_name'),
            info=i18n.t('components.models.embedding_model.max_retries.info'),
            advanced=True,
            value=3
        ),
        BoolInput(
            name="show_progress_bar",
            display_name=i18n.t(
                'components.models.embedding_model.show_progress_bar.display_name'),
            info=i18n.t(
                'components.models.embedding_model.show_progress_bar.info'),
            advanced=True
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.models.embedding_model.model_kwargs.display_name'),
            info=i18n.t('components.models.embedding_model.model_kwargs.info'),
            advanced=True,
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        provider = self.provider
        model = self.model
        api_key = self.api_key
        api_base = self.api_base
        dimensions = self.dimensions
        chunk_size = self.chunk_size
        request_timeout = self.request_timeout
        max_retries = self.max_retries
        show_progress_bar = self.show_progress_bar
        model_kwargs = self.model_kwargs or {}

        if provider == "OpenAI":
            if not api_key:
                error_message = i18n.t(
                    'components.models.embedding_model.errors.openai_api_key_required')
                self.status = error_message
                raise ValueError(error_message)

            try:
                success_message = i18n.t('components.models.embedding_model.success.openai_embeddings_created',
                                         model=model)
                self.status = success_message

                return OpenAIEmbeddings(
                    model=model,
                    dimensions=dimensions or None,
                    base_url=api_base or None,
                    api_key=api_key,
                    chunk_size=chunk_size,
                    max_retries=max_retries,
                    timeout=request_timeout or None,
                    show_progress_bar=show_progress_bar,
                    model_kwargs=model_kwargs,
                )
            except Exception as e:
                error_message = i18n.t('components.models.embedding_model.errors.failed_to_create_embeddings',
                                       provider=provider, error=str(e))
                self.status = error_message
                raise ValueError(error_message) from e

        error_message = i18n.t(
            'components.models.embedding_model.errors.unknown_provider', provider=provider)
        self.status = error_message
        raise ValueError(error_message)

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None) -> dotdict:
        if field_name == "provider" and field_value == "OpenAI":
            build_config["model"]["options"] = OPENAI_EMBEDDING_MODEL_NAMES
            build_config["model"]["value"] = OPENAI_EMBEDDING_MODEL_NAMES[0]
            build_config["api_key"]["display_name"] = i18n.t(
                'components.models.embedding_model.api_key.openai_display_name')
            build_config["api_base"]["display_name"] = i18n.t(
                'components.models.embedding_model.api_base.openai_display_name')
        return build_config
