import os
import i18n
from typing import Any

import requests
from pydantic.v1 import SecretStr

from lfx.base.models.google_generative_ai_constants import GOOGLE_GENERATIVE_AI_MODELS
from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import BoolInput, DropdownInput, FloatInput, IntInput, SecretStrInput, SliderInput
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict


class GoogleGenerativeAIComponent(LCModelComponent):
    display_name = "Google Generative AI"
    description = i18n.t('components.google.google_generative_ai.description')
    icon = "GoogleGenerativeAI"
    name = "GoogleGenerativeAIModel"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_output_tokens",
            display_name=i18n.t(
                'components.google.google_generative_ai.max_output_tokens.display_name'),
            info=i18n.t(
                'components.google.google_generative_ai.max_output_tokens.info')
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.google.google_generative_ai.model_name.display_name'),
            info=i18n.t(
                'components.google.google_generative_ai.model_name.info'),
            options=GOOGLE_GENERATIVE_AI_MODELS,
            value="gemini-1.5-pro",
            refresh_button=True,
            combobox=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.google.google_generative_ai.api_key.display_name'),
            info=i18n.t('components.google.google_generative_ai.api_key.info'),
            required=True,
            real_time_refresh=True,
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t(
                'components.google.google_generative_ai.top_p.display_name'),
            info=i18n.t('components.google.google_generative_ai.top_p.info'),
            advanced=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.google.google_generative_ai.temperature.display_name'),
            value=0.1,
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            info=i18n.t(
                'components.google.google_generative_ai.temperature.info'),
        ),
        IntInput(
            name="n",
            display_name=i18n.t(
                'components.google.google_generative_ai.n.display_name'),
            info=i18n.t('components.google.google_generative_ai.n.info'),
            advanced=True,
        ),
        IntInput(
            name="top_k",
            display_name=i18n.t(
                'components.google.google_generative_ai.top_k.display_name'),
            info=i18n.t('components.google.google_generative_ai.top_k.info'),
            advanced=True,
        ),
        BoolInput(
            name="tool_model_enabled",
            display_name=i18n.t(
                'components.google.google_generative_ai.tool_model_enabled.display_name'),
            info=i18n.t(
                'components.google.google_generative_ai.tool_model_enabled.info'),
            value=False,
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build Google Generative AI model.

        Returns:
            LanguageModel: Configured ChatGoogleGenerativeAI instance.

        Raises:
            ImportError: If langchain_google_genai package is not installed.
        """
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            error_msg = i18n.t(
                'components.google.google_generative_ai.errors.package_not_installed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        logger.info(i18n.t('components.google.google_generative_ai.logs.building_model',
                           model=self.model_name))

        google_api_key = self.api_key
        model = self.model_name
        max_output_tokens = self.max_output_tokens
        temperature = self.temperature
        top_k = self.top_k
        top_p = self.top_p
        n = self.n

        logger.debug(i18n.t('components.google.google_generative_ai.logs.model_parameters',
                            max_tokens=max_output_tokens or 'default',
                            temperature=temperature,
                            top_k=top_k or 'default',
                            top_p=top_p or 'default',
                            n=n or 1))

        model_instance = ChatGoogleGenerativeAI(
            model=model,
            max_output_tokens=max_output_tokens or None,
            temperature=temperature,
            top_k=top_k or None,
            top_p=top_p or None,
            n=n or 1,
            google_api_key=SecretStr(google_api_key).get_secret_value(),
        )

        logger.info(
            i18n.t('components.google.google_generative_ai.logs.model_built'))
        return model_instance

    def get_models(self, *, tool_model_enabled: bool | None = None) -> list[str]:
        """Get available Google Generative AI models.

        Args:
            tool_model_enabled: If True, filter models that support tool calling.

        Returns:
            list[str]: List of available model IDs.
        """
        logger.debug(i18n.t('components.google.google_generative_ai.logs.fetching_models',
                            tool_enabled=tool_model_enabled or False))

        try:
            import google.generativeai as genai

            logger.debug(
                i18n.t('components.google.google_generative_ai.logs.configuring_api'))
            genai.configure(api_key=self.api_key)

            logger.debug(
                i18n.t('components.google.google_generative_ai.logs.listing_models'))
            model_ids = [
                model.name.replace("models/", "")
                for model in genai.list_models()
                if "generateContent" in model.supported_generation_methods
            ]
            model_ids.sort(reverse=True)

            logger.info(i18n.t('components.google.google_generative_ai.logs.models_fetched',
                               count=len(model_ids)))

        except (ImportError, ValueError) as e:
            logger.exception(i18n.t('components.google.google_generative_ai.logs.model_fetch_error',
                                    error=str(e)))
            model_ids = GOOGLE_GENERATIVE_AI_MODELS

        if tool_model_enabled:
            logger.debug(
                i18n.t('components.google.google_generative_ai.logs.filtering_tool_models'))

            try:
                from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
            except ImportError as e:
                error_msg = i18n.t(
                    'components.google.google_generative_ai.errors.langchain_not_installed')
                logger.error(error_msg)
                raise ImportError(error_msg) from e

            filtered_models = []
            for model in model_ids:
                try:
                    model_with_tool = ChatGoogleGenerativeAI(
                        model=model,
                        google_api_key=self.api_key,
                    )
                    if self.supports_tool_calling(model_with_tool):
                        filtered_models.append(model)
                        logger.debug(i18n.t('components.google.google_generative_ai.logs.tool_support_confirmed',
                                            model=model))
                    else:
                        logger.debug(i18n.t('components.google.google_generative_ai.logs.tool_support_not_found',
                                            model=model))
                except Exception as e:
                    logger.debug(i18n.t('components.google.google_generative_ai.logs.tool_check_failed',
                                        model=model,
                                        error=str(e)))

            model_ids = filtered_models
            logger.info(i18n.t('components.google.google_generative_ai.logs.tool_models_filtered',
                               count=len(model_ids)))

        return model_ids

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        """Update build configuration when inputs change.

        Args:
            build_config: The build configuration to update.
            field_value: The new field value.
            field_name: The name of the field that changed.

        Returns:
            dotdict: Updated build configuration.
        """
        if field_name in {"base_url", "model_name", "tool_model_enabled", "api_key"} and field_value:
            logger.debug(i18n.t('components.google.google_generative_ai.logs.updating_config',
                                field=field_name))

            try:
                if len(self.api_key) == 0:
                    logger.debug(
                        i18n.t('components.google.google_generative_ai.logs.no_api_key'))
                    ids = GOOGLE_GENERATIVE_AI_MODELS
                else:
                    try:
                        logger.debug(
                            i18n.t('components.google.google_generative_ai.logs.fetching_available_models'))
                        ids = self.get_models(
                            tool_model_enabled=self.tool_model_enabled)
                    except (ImportError, ValueError, requests.exceptions.RequestException) as e:
                        logger.exception(i18n.t('components.google.google_generative_ai.logs.model_fetch_fallback',
                                                error=str(e)))
                        ids = GOOGLE_GENERATIVE_AI_MODELS

                build_config.setdefault("model_name", {})
                build_config["model_name"]["options"] = ids
                build_config["model_name"].setdefault("value", ids[0])

                logger.debug(i18n.t('components.google.google_generative_ai.logs.config_updated',
                                    model_count=len(ids),
                                    default_model=ids[0] if ids else 'none'))

            except Exception as e:
                error_msg = i18n.t('components.google.google_generative_ai.errors.config_update_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

        return build_config
