import os
import i18n
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr
from typing_extensions import override

from lfx.base.models.aiml_constants import AimlModels
from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import (
    DictInput,
    DropdownInput,
    IntInput,
    SecretStrInput,
    SliderInput,
    StrInput,
)
from lfx.log.logger import logger


class AIMLModelComponent(LCModelComponent):
    display_name = i18n.t('components.aiml.aiml.display_name')
    description = i18n.t('components.aiml.aiml.description')
    icon = "AIML"
    name = "AIMLModel"
    documentation = "https://docs.aimlapi.com/api-reference"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.aiml.aiml.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.aiml.aiml.max_tokens.info'),
            range_spec=RangeSpec(min=0, max=128000),
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.aiml.aiml.model_kwargs.display_name'),
            advanced=True,
            info=i18n.t('components.aiml.aiml.model_kwargs.info'),
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.aiml.aiml.model_name.display_name'),
            advanced=False,
            options=[],
            refresh_button=True,
            info=i18n.t('components.aiml.aiml.model_name.info'),
        ),
        StrInput(
            name="aiml_api_base",
            display_name=i18n.t(
                'components.aiml.aiml.aiml_api_base.display_name'),
            advanced=True,
            info=i18n.t('components.aiml.aiml.aiml_api_base.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t('components.aiml.aiml.api_key.display_name'),
            info=i18n.t('components.aiml.aiml.api_key.info'),
            advanced=False,
            value="AIML_API_KEY",
            required=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.aiml.aiml.temperature.display_name'),
            value=0.1,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            info=i18n.t('components.aiml.aiml.temperature.info'),
        ),
    ]

    @override
    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        """Update build configuration when model-related fields change."""
        try:
            if field_name in {"api_key", "aiml_api_base", "model_name"}:
                try:
                    self.status = i18n.t(
                        'components.aiml.aiml.status.loading_models')
                    aiml = AimlModels()
                    aiml.get_aiml_models()
                    build_config["model_name"]["options"] = aiml.chat_models

                    if aiml.chat_models:
                        success_msg = i18n.t('components.aiml.aiml.success.models_loaded',
                                             count=len(aiml.chat_models))
                        logger.info(success_msg)
                        self.status = success_msg
                    else:
                        warning_msg = i18n.t(
                            'components.aiml.aiml.warnings.no_models_available')
                        logger.warning(warning_msg)
                        self.status = warning_msg

                except Exception as e:
                    error_msg = i18n.t(
                        'components.aiml.aiml.errors.models_loading_failed', error=str(e))
                    logger.exception(error_msg)
                    self.status = error_msg
                    build_config["model_name"]["options"] = []

            return build_config

        except Exception as e:
            error_msg = i18n.t(
                'components.aiml.aiml.errors.build_config_update_failed', error=str(e))
            logger.exception(error_msg)
            return build_config

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build and return the AI/ML language model."""
        try:
            # Validate required inputs
            if not self.api_key:
                error_msg = i18n.t(
                    'components.aiml.aiml.errors.api_key_required')
                raise ValueError(error_msg)

            if not self.model_name:
                error_msg = i18n.t(
                    'components.aiml.aiml.errors.model_name_required')
                raise ValueError(error_msg)

            self.status = i18n.t(
                'components.aiml.aiml.status.initializing_model', model=self.model_name)

            aiml_api_key = self.api_key
            temperature = self.temperature
            model_name: str = self.model_name
            max_tokens = self.max_tokens
            model_kwargs = self.model_kwargs or {}
            aiml_api_base = self.aiml_api_base or "https://api.aimlapi.com/v2"

            # Extract API key from SecretStr if needed
            try:
                openai_api_key = aiml_api_key.get_secret_value() if isinstance(
                    aiml_api_key, SecretStr) else aiml_api_key
            except Exception as e:
                error_msg = i18n.t(
                    'components.aiml.aiml.errors.api_key_extraction_failed', error=str(e))
                raise ValueError(error_msg) from e

            # TODO: Once OpenAI fixes their o1 models, this part will need to be removed
            # to work correctly with o1 temperature settings.
            if "o1" in model_name:
                temperature = 1
                logger.info(
                    i18n.t('components.aiml.aiml.logs.o1_temperature_override', model=model_name))

            try:
                model = ChatOpenAI(
                    model=model_name,
                    temperature=temperature,
                    api_key=openai_api_key,
                    base_url=aiml_api_base,
                    max_tokens=max_tokens or None,
                    **model_kwargs,
                )

                success_msg = i18n.t('components.aiml.aiml.success.model_initialized',
                                     model=model_name, base_url=aiml_api_base)
                logger.info(success_msg)
                self.status = success_msg

                return model

            except Exception as e:
                error_msg = i18n.t('components.aiml.aiml.errors.model_initialization_failed',
                                   model=model_name, error=str(e))
                raise RuntimeError(error_msg) from e

        except (ValueError, RuntimeError) as e:
            # Re-raise these as they already have i18n messages
            raise
        except Exception as e:
            error_msg = i18n.t(
                'components.aiml.aiml.errors.model_build_failed', error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _get_exception_message(self, e: Exception):
        """Get a message from an OpenAI exception.

        Args:
            e (Exception): The exception to get the message from.

        Returns:
            str: The message from the exception.
        """
        try:
            try:
                from openai.error import BadRequestError
            except ImportError:
                logger.debug(
                    i18n.t('components.aiml.aiml.logs.openai_error_not_available'))
                return None

            if isinstance(e, BadRequestError):
                message = e.json_body.get("error", {}).get("message", "")
                if message:
                    logger.debug(
                        i18n.t('components.aiml.aiml.logs.extracted_error_message', message=message))
                    return message
            return None

        except Exception as ex:
            error_msg = i18n.t(
                'components.aiml.aiml.errors.exception_message_extraction_failed', error=str(ex))
            logger.warning(error_msg)
            return None
