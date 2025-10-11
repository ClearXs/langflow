import os
import i18n
import requests
from pydantic.v1 import SecretStr
from typing_extensions import override

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import BoolInput, DictInput, DropdownInput, IntInput, SecretStrInput, SliderInput, StrInput
from lfx.log.logger import logger

DEEPSEEK_MODELS = ["deepseek-chat"]


class DeepSeekModelComponent(LCModelComponent):
    display_name = "DeepSeek"
    description = i18n.t('components.deepseek.deepseek.description')
    icon = "DeepSeek"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.deepseek.deepseek.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.deepseek.deepseek.max_tokens.info'),
            range_spec=RangeSpec(min=0, max=128000),
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.deepseek.deepseek.model_kwargs.display_name'),
            advanced=True,
            info=i18n.t('components.deepseek.deepseek.model_kwargs.info'),
        ),
        BoolInput(
            name="json_mode",
            display_name=i18n.t(
                'components.deepseek.deepseek.json_mode.display_name'),
            advanced=True,
            info=i18n.t('components.deepseek.deepseek.json_mode.info'),
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.deepseek.deepseek.model_name.display_name'),
            info=i18n.t('components.deepseek.deepseek.model_name.info'),
            options=DEEPSEEK_MODELS,
            value="deepseek-chat",
            refresh_button=True,
        ),
        StrInput(
            name="api_base",
            display_name=i18n.t(
                'components.deepseek.deepseek.api_base.display_name'),
            advanced=True,
            info=i18n.t('components.deepseek.deepseek.api_base.info'),
            value="https://api.deepseek.com",
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.deepseek.deepseek.api_key.display_name'),
            info=i18n.t('components.deepseek.deepseek.api_key.info'),
            advanced=False,
            required=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.deepseek.deepseek.temperature.display_name'),
            info=i18n.t('components.deepseek.deepseek.temperature.info'),
            value=1.0,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            advanced=True,
        ),
        IntInput(
            name="seed",
            display_name=i18n.t(
                'components.deepseek.deepseek.seed.display_name'),
            info=i18n.t('components.deepseek.deepseek.seed.info'),
            advanced=True,
            value=1,
        ),
    ]

    def get_models(self) -> list[str]:
        """Fetch available models from DeepSeek API.

        Returns:
            list[str]: List of available model IDs.
        """
        if not self.api_key:
            logger.warning(
                i18n.t('components.deepseek.deepseek.logs.no_api_key'))
            return DEEPSEEK_MODELS

        url = f"{self.api_base}/models"
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Accept": "application/json"}

        try:
            logger.info(i18n.t('components.deepseek.deepseek.logs.fetching_models',
                               url=url))
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            model_list = response.json()
            models = [model["id"] for model in model_list.get("data", [])]

            logger.info(i18n.t('components.deepseek.deepseek.logs.models_fetched',
                               count=len(models)))
            return models

        except requests.RequestException as e:
            error_msg = i18n.t('components.deepseek.deepseek.errors.fetch_models_failed',
                               error=str(e))
            logger.error(error_msg)
            self.status = error_msg
            return DEEPSEEK_MODELS

    @override
    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        """Update build configuration when certain fields change.

        Args:
            build_config: The build configuration dictionary.
            field_value: The new field value.
            field_name: The name of the field being updated.

        Returns:
            dict: The updated build configuration.
        """
        if field_name in {"api_key", "api_base", "model_name"}:
            logger.debug(
                i18n.t('components.deepseek.deepseek.logs.updating_models_list'))
            models = self.get_models()
            build_config["model_name"]["options"] = models
            logger.debug(i18n.t('components.deepseek.deepseek.logs.models_list_updated',
                                count=len(models)))
        return build_config

    def build_model(self) -> LanguageModel:
        """Build and configure the DeepSeek language model.

        Returns:
            LanguageModel: Configured DeepSeek chat model.

        Raises:
            ImportError: If langchain-openai is not installed.
            ValueError: If model initialization fails.
        """
        try:
            from langchain_openai import ChatOpenAI
            logger.debug(
                i18n.t('components.deepseek.deepseek.logs.langchain_import_successful'))
        except ImportError as e:
            error_msg = i18n.t(
                'components.deepseek.deepseek.errors.langchain_import_failed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        try:
            api_key = SecretStr(
                self.api_key).get_secret_value() if self.api_key else None

            logger.info(i18n.t('components.deepseek.deepseek.logs.building_model',
                               model=self.model_name,
                               temperature=self.temperature if self.temperature is not None else 0.1,
                               max_tokens=self.max_tokens or "unlimited"))

            output = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature if self.temperature is not None else 0.1,
                max_tokens=self.max_tokens or None,
                model_kwargs=self.model_kwargs or {},
                base_url=self.api_base,
                api_key=api_key,
                streaming=self.stream if hasattr(self, "stream") else False,
                seed=self.seed,
            )

            if self.json_mode:
                output = output.bind(response_format={"type": "json_object"})
                logger.debug(
                    i18n.t('components.deepseek.deepseek.logs.json_mode_enabled'))

            logger.info(
                i18n.t('components.deepseek.deepseek.logs.model_built'))
            return output

        except Exception as e:
            error_msg = i18n.t('components.deepseek.deepseek.errors.build_model_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _get_exception_message(self, e: Exception):
        """Get message from DeepSeek API exception.

        Args:
            e: The exception to extract message from.

        Returns:
            str | None: The error message if available.
        """
        try:
            from openai import BadRequestError

            if isinstance(e, BadRequestError):
                message = e.body.get("message")
                if message:
                    logger.debug(i18n.t('components.deepseek.deepseek.logs.extracted_error_message',
                                        message=message))
                    return message
        except ImportError:
            logger.debug(
                i18n.t('components.deepseek.deepseek.logs.openai_not_available'))
        return None
