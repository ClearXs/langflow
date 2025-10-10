import os
import i18n
import json
from typing import Any

import requests
from langchain_ibm import ChatWatsonx
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import BoolInput, DropdownInput, IntInput, SecretStrInput, SliderInput, StrInput
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict


class WatsonxAIComponent(LCModelComponent):
    display_name = "IBM watsonx.ai"
    description = i18n.t('components.ibm.watsonx.description')
    icon = "WatsonxAI"
    name = "IBMwatsonxModel"
    beta = False

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    _default_models = ["ibm/granite-3-2b-instruct",
                       "ibm/granite-3-8b-instruct", "ibm/granite-13b-instruct-v2"]

    inputs = [
        *LCModelComponent.get_base_inputs(),
        DropdownInput(
            name="url",
            display_name=i18n.t('components.ibm.watsonx.url.display_name'),
            info=i18n.t('components.ibm.watsonx.url.info'),
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
                'components.ibm.watsonx.project_id.display_name'),
            required=True,
            info=i18n.t('components.ibm.watsonx.project_id.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t('components.ibm.watsonx.api_key.display_name'),
            info=i18n.t('components.ibm.watsonx.api_key.info'),
            required=True,
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.ibm.watsonx.model_name.display_name'),
            options=[],
            value=None,
            dynamic=True,
            required=True,
        ),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.ibm.watsonx.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.ibm.watsonx.max_tokens.info'),
            range_spec=RangeSpec(min=1, max=4096),
            value=1000,
        ),
        StrInput(
            name="stop_sequence",
            display_name=i18n.t(
                'components.ibm.watsonx.stop_sequence.display_name'),
            advanced=True,
            info=i18n.t('components.ibm.watsonx.stop_sequence.info'),
            field_type="str",
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.ibm.watsonx.temperature.display_name'),
            info=i18n.t('components.ibm.watsonx.temperature.info'),
            value=0.1,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            advanced=True,
        ),
        SliderInput(
            name="top_p",
            display_name=i18n.t('components.ibm.watsonx.top_p.display_name'),
            info=i18n.t('components.ibm.watsonx.top_p.info'),
            value=0.9,
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
        ),
        SliderInput(
            name="frequency_penalty",
            display_name=i18n.t(
                'components.ibm.watsonx.frequency_penalty.display_name'),
            info=i18n.t('components.ibm.watsonx.frequency_penalty.info'),
            value=0.5,
            range_spec=RangeSpec(min=-2.0, max=2.0, step=0.01),
            advanced=True,
        ),
        SliderInput(
            name="presence_penalty",
            display_name=i18n.t(
                'components.ibm.watsonx.presence_penalty.display_name'),
            info=i18n.t('components.ibm.watsonx.presence_penalty.info'),
            value=0.3,
            range_spec=RangeSpec(min=-2.0, max=2.0, step=0.01),
            advanced=True,
        ),
        IntInput(
            name="seed",
            display_name=i18n.t('components.ibm.watsonx.seed.display_name'),
            advanced=True,
            info=i18n.t('components.ibm.watsonx.seed.info'),
            value=8,
        ),
        BoolInput(
            name="logprobs",
            display_name=i18n.t(
                'components.ibm.watsonx.logprobs.display_name'),
            advanced=True,
            info=i18n.t('components.ibm.watsonx.logprobs.info'),
            value=True,
        ),
        IntInput(
            name="top_logprobs",
            display_name=i18n.t(
                'components.ibm.watsonx.top_logprobs.display_name'),
            advanced=True,
            info=i18n.t('components.ibm.watsonx.top_logprobs.info'),
            value=3,
            range_spec=RangeSpec(min=1, max=20),
        ),
        StrInput(
            name="logit_bias",
            display_name=i18n.t(
                'components.ibm.watsonx.logit_bias.display_name'),
            advanced=True,
            info=i18n.t('components.ibm.watsonx.logit_bias.info'),
            field_type="str",
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
        logger.debug(i18n.t('components.ibm.watsonx.logs.fetching_models',
                            base_url=base_url))

        try:
            endpoint = f"{base_url}/ml/v1/foundation_model_specs"
            params = {"version": "2024-09-16",
                      "filters": "function_text_chat,!lifecycle_withdrawn"}

            logger.debug(i18n.t('components.ibm.watsonx.logs.requesting_models',
                                endpoint=endpoint))

            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            models = [model["model_id"] for model in data.get("resources", [])]

            logger.info(i18n.t('components.ibm.watsonx.logs.models_fetched',
                               count=len(models)))

            return sorted(models)

        except Exception as e:
            error_msg = i18n.t('components.ibm.watsonx.errors.fetch_failed',
                               error=str(e))
            logger.exception(error_msg)
            logger.info(i18n.t('components.ibm.watsonx.logs.using_default_models',
                               count=len(WatsonxAIComponent._default_models)))
            return WatsonxAIComponent._default_models

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        """Update model options when URL or API key changes.

        Args:
            build_config: The build configuration to update.
            field_value: The new field value.
            field_name: The name of the field that changed.

        Returns:
            dotdict: Updated build configuration.
        """
        logger.info(i18n.t('components.ibm.watsonx.logs.updating_config',
                           field=field_name or 'unknown',
                           value=str(field_value)[:50]))

        if field_name == "url" and field_value:
            try:
                logger.debug(i18n.t('components.ibm.watsonx.logs.fetching_models_for_url',
                                    url=build_config.url.value))

                models = self.fetch_models(base_url=build_config.url.value)
                build_config.model_name.options = models

                if build_config.model_name.value:
                    build_config.model_name.value = models[0]

                info_message = i18n.t('components.ibm.watsonx.logs.models_updated',
                                      count=len(models),
                                      url=build_config.url.value)
                logger.info(info_message)

            except Exception as e:
                error_msg = i18n.t('components.ibm.watsonx.errors.config_update_failed',
                                   error=str(e))
                logger.exception(error_msg)

        return build_config

    def build_model(self) -> LanguageModel:
        """Build watsonx.ai language model.

        Returns:
            LanguageModel: Configured ChatWatsonx instance.
        """
        logger.info(i18n.t('components.ibm.watsonx.logs.building_model',
                           model=self.model_name,
                           url=self.url))

        # Parse logit_bias from JSON string if provided
        logit_bias = None
        if hasattr(self, "logit_bias") and self.logit_bias:
            try:
                logger.debug(
                    i18n.t('components.ibm.watsonx.logs.parsing_logit_bias'))
                logit_bias = json.loads(self.logit_bias)
                logger.debug(i18n.t('components.ibm.watsonx.logs.logit_bias_parsed',
                                    bias=str(logit_bias)))
            except json.JSONDecodeError as e:
                error_msg = i18n.t('components.ibm.watsonx.errors.invalid_logit_bias',
                                   error=str(e))
                logger.warning(error_msg)
                logit_bias = {"1003": -100, "1004": -100}
                logger.info(
                    i18n.t('components.ibm.watsonx.logs.using_default_logit_bias'))

        logger.debug(i18n.t('components.ibm.watsonx.logs.configuring_parameters',
                            max_tokens=getattr(self, "max_tokens", 1000),
                            temperature=getattr(self, "temperature", 0.1),
                            top_p=getattr(self, "top_p", 0.9),
                            streaming=self.stream))

        chat_params = {
            "max_tokens": getattr(self, "max_tokens", None),
            "temperature": getattr(self, "temperature", None),
            "top_p": getattr(self, "top_p", None),
            "frequency_penalty": getattr(self, "frequency_penalty", None),
            "presence_penalty": getattr(self, "presence_penalty", None),
            "seed": getattr(self, "seed", None),
            "stop": [self.stop_sequence] if self.stop_sequence else [],
            "n": 1,
            "logprobs": getattr(self, "logprobs", True),
            "top_logprobs": getattr(self, "top_logprobs", None),
            "time_limit": 600000,
            "logit_bias": logit_bias,
        }

        logger.debug(
            i18n.t('components.ibm.watsonx.logs.creating_chat_instance'))

        model = ChatWatsonx(
            apikey=SecretStr(self.api_key).get_secret_value(),
            url=self.url,
            project_id=self.project_id,
            model_id=self.model_name,
            params=chat_params,
            streaming=self.stream,
        )

        logger.info(i18n.t('components.ibm.watsonx.logs.model_built'))
        return model
