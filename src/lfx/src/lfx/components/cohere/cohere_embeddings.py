import os
from typing import Any

import cohere
import i18n
from langchain_cohere import CohereEmbeddings

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import Embeddings
from lfx.io import DropdownInput, FloatInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.log.logger import logger

HTTP_STATUS_OK = 200


class CohereEmbeddingsComponent(LCModelComponent):
    display_name = i18n.t('components.cohere.cohere_embeddings.display_name')
    description = i18n.t('components.cohere.cohere_embeddings.description')
    icon = "Cohere"
    name = "CohereEmbeddings"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.cohere.cohere_embeddings.api_key.display_name'),
            required=True,
            real_time_refresh=True
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.cohere.cohere_embeddings.model_name.display_name'),
            advanced=False,
            options=[
                "embed-english-v2.0",
                "embed-multilingual-v2.0",
                "embed-english-light-v2.0",
                "embed-multilingual-light-v2.0",
            ],
            value="embed-english-v2.0",
            refresh_button=True,
            combobox=True,
            info=i18n.t('components.cohere.cohere_embeddings.model_name.info'),
        ),
        MessageTextInput(
            name="truncate",
            display_name=i18n.t(
                'components.cohere.cohere_embeddings.truncate.display_name'),
            info=i18n.t('components.cohere.cohere_embeddings.truncate.info'),
            advanced=True
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.cohere.cohere_embeddings.max_retries.display_name'),
            info=i18n.t(
                'components.cohere.cohere_embeddings.max_retries.info'),
            value=3,
            advanced=True
        ),
        MessageTextInput(
            name="user_agent",
            display_name=i18n.t(
                'components.cohere.cohere_embeddings.user_agent.display_name'),
            info=i18n.t('components.cohere.cohere_embeddings.user_agent.info'),
            advanced=True,
            value="langchain"
        ),
        FloatInput(
            name="request_timeout",
            display_name=i18n.t(
                'components.cohere.cohere_embeddings.request_timeout.display_name'),
            info=i18n.t(
                'components.cohere.cohere_embeddings.request_timeout.info'),
            advanced=True
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.cohere.cohere_embeddings.outputs.embeddings.display_name'),
            name="embeddings",
            method="build_embeddings"
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        data = None
        try:
            self.status = i18n.t(
                'components.cohere.cohere_embeddings.status.initializing')
            logger.info(i18n.t('components.cohere.cohere_embeddings.logs.initializing',
                               model=self.model_name))

            data = CohereEmbeddings(
                cohere_api_key=self.api_key,
                model=self.model_name,
                truncate=self.truncate,
                max_retries=self.max_retries,
                user_agent=self.user_agent,
                request_timeout=self.request_timeout or None,
            )

            success_msg = i18n.t('components.cohere.cohere_embeddings.success.embeddings_created',
                                 model=self.model_name)
            self.status = success_msg
            logger.info(success_msg)

        except Exception as e:
            error_msg = i18n.t('components.cohere.cohere_embeddings.errors.creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

        return data

    def get_model(self):
        try:
            logger.debug(
                i18n.t('components.cohere.cohere_embeddings.logs.fetching_models'))

            co = cohere.ClientV2(self.api_key)
            response = co.models.list(endpoint="embed")
            models = response.models
            model_names = [model.name for model in models]

            logger.info(i18n.t('components.cohere.cohere_embeddings.logs.models_fetched',
                               count=len(model_names)))

            return model_names

        except Exception as e:
            error_msg = i18n.t('components.cohere.cohere_embeddings.errors.fetch_models_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    async def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None):
        if field_name in {"model_name", "api_key"}:
            if build_config.get("api_key", {}).get("value", None):
                logger.debug(
                    i18n.t('components.cohere.cohere_embeddings.logs.updating_model_list'))
                build_config["model_name"]["options"] = self.get_model()
        else:
            build_config["model_name"]["options"] = field_value
        return build_config
