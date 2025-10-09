import i18n
from typing import Any

import requests
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames
from langchain_ibm import WatsonxEmbeddings
from pydantic.v1 import SecretStr

from lfx.base.embeddings.model import LCEmbeddingsModel
from lfx.field_typing import Embeddings
from lfx.io import BoolInput, DropdownInput, IntInput, SecretStrInput, StrInput
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict


class WatsonxEmbeddingsComponent(LCEmbeddingsModel):
    display_name = "IBM watsonx.ai Embeddings"
    description = i18n.t('components.ibm.watsonx_embeddings.description')
    icon = "WatsonxAI"
    name = "WatsonxEmbeddingsComponent"

    # models present in all the regions
    _default_models = [
        "sentence-transformers/all-minilm-l12-v2",
        "ibm/slate-125m-english-rtrvr-v2",
        "ibm/slate-30m-english-rtrvr-v2",
        "intfloat/multilingual-e5-large",
    ]

    inputs = [
        DropdownInput(
            name="url",
            display_name=i18n.t(
                'components.ibm.watsonx_embeddings.url.display_name'),
            info=i18n.t('components.ibm.watsonx_embeddings.url.info'),
            value=None,
            options=[
                "https://us-south.ml.cloud.ibm.com",
                "https://eu-de.ml.cloud.ibm.com",
                "https://eu-gb.ml.cloud.ibm.com",
                "https://au-syd.ml.cloud.ibm.com",
                "https://jp-tok.ml.cloud.ibm.com",
                "https://ca-tor.ml.cloud.ibm.com",
            ],
            real_time_refresh=True,
        ),
        StrInput(
            name="project_id",
            display_name=i18n.t(
                'components.ibm.watsonx_embeddings.project_id.display_name'),
            info=i18n.t('components.ibm.watsonx_embeddings.project_id.info'),
            required=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.ibm.watsonx_embeddings.api_key.display_name'),
            info=i18n.t('components.ibm.watsonx_embeddings.api_key.info'),
            required=True,
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.ibm.watsonx_embeddings.model_name.display_name'),
            options=[],
            value=None,
            dynamic=True,
            required=True,
        ),
        IntInput(
            name="truncate_input_tokens",
            display_name=i18n.t(
                'components.ibm.watsonx_embeddings.truncate_input_tokens.display_name'),
            advanced=True,
            value=200,
        ),
        BoolInput(
            name="input_text",
            display_name=i18n.t(
                'components.ibm.watsonx_embeddings.input_text.display_name'),
            value=True,
            advanced=True,
        ),
    ]

    @staticmethod
    def fetch_models(base_url: str) -> list[str]:
        """Fetch available models from the watsonx.ai API.

        Args:
            base_url: The base URL of the watsonx.ai API.

        Returns:
            list[str]: List of available model IDs.
        """
        logger.debug(i18n.t('components.ibm.watsonx_embeddings.logs.fetching_models',
                            base_url=base_url))

        try:
            endpoint = f"{base_url}/ml/v1/foundation_model_specs"
            params = {
                "version": "2024-09-16",
                "filters": "function_embedding,!lifecycle_withdrawn:and",
            }

            logger.debug(i18n.t('components.ibm.watsonx_embeddings.logs.requesting_models',
                                endpoint=endpoint))

            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            models = [model["model_id"] for model in data.get("resources", [])]

            logger.info(i18n.t('components.ibm.watsonx_embeddings.logs.models_fetched',
                               count=len(models),
                               base_url=base_url))

            return sorted(models)

        except requests.exceptions.Timeout:
            error_msg = i18n.t(
                'components.ibm.watsonx_embeddings.errors.fetch_timeout')
            logger.error(error_msg)
            return WatsonxEmbeddingsComponent._default_models

        except requests.exceptions.HTTPError as e:
            error_msg = i18n.t('components.ibm.watsonx_embeddings.errors.fetch_http_error',
                               status=e.response.status_code if e.response else 'unknown')
            logger.error(error_msg)
            return WatsonxEmbeddingsComponent._default_models

        except Exception as e:
            error_msg = i18n.t('components.ibm.watsonx_embeddings.errors.fetch_failed',
                               error=str(e))
            logger.exception(error_msg)
            return WatsonxEmbeddingsComponent._default_models

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        """Update model options when URL or API key changes.

        Args:
            build_config: The build configuration to update.
            field_value: The new field value.
            field_name: The name of the field that changed.

        Returns:
            dotdict: Updated build configuration.
        """
        logger.debug(i18n.t('components.ibm.watsonx_embeddings.logs.updating_config',
                            field=field_name or 'unknown',
                            value=str(field_value)[:50]))

        if field_name == "url" and field_value:
            try:
                logger.debug(i18n.t('components.ibm.watsonx_embeddings.logs.fetching_models_for_url',
                                    url=build_config.url.value))

                models = self.fetch_models(base_url=build_config.url.value)
                build_config.model_name.options = models

                if build_config.model_name.value:
                    build_config.model_name.value = models[0]

                info_message = i18n.t('components.ibm.watsonx_embeddings.logs.models_updated',
                                      count=len(models),
                                      url=build_config.url.value)
                logger.info(info_message)

            except Exception as e:
                error_msg = i18n.t('components.ibm.watsonx_embeddings.errors.config_update_failed',
                                   error=str(e))
                logger.exception(error_msg)

        return build_config

    def build_embeddings(self) -> Embeddings:
        """Build watsonx.ai embeddings instance.

        Returns:
            Embeddings: Configured embeddings instance.
        """
        logger.info(i18n.t('components.ibm.watsonx_embeddings.logs.building_embeddings',
                           model=self.model_name,
                           url=self.url))

        try:
            logger.debug(
                i18n.t('components.ibm.watsonx_embeddings.logs.creating_credentials'))
            credentials = Credentials(
                api_key=SecretStr(self.api_key).get_secret_value(),
                url=self.url,
            )

            logger.debug(
                i18n.t('components.ibm.watsonx_embeddings.logs.creating_api_client'))
            api_client = APIClient(credentials)

            logger.debug(i18n.t('components.ibm.watsonx_embeddings.logs.configuring_parameters',
                                truncate_tokens=self.truncate_input_tokens,
                                include_text=self.input_text))

            params = {
                EmbedTextParamsMetaNames.TRUNCATE_INPUT_TOKENS: self.truncate_input_tokens,
                EmbedTextParamsMetaNames.RETURN_OPTIONS: {"input_text": self.input_text},
            }

            logger.debug(
                i18n.t('components.ibm.watsonx_embeddings.logs.creating_embeddings_instance'))
            embeddings = WatsonxEmbeddings(
                model_id=self.model_name,
                params=params,
                watsonx_client=api_client,
                project_id=self.project_id,
            )

            logger.info(
                i18n.t('components.ibm.watsonx_embeddings.logs.embeddings_built'))
            return embeddings

        except Exception as e:
            error_msg = i18n.t('components.ibm.watsonx_embeddings.errors.build_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise
