import os
from typing import Any, cast

import i18n
import requests
from pydantic import ValidationError

from lfx.base.models.anthropic_constants import (
    ANTHROPIC_MODELS,
    DEFAULT_ANTHROPIC_API_URL,
    TOOL_CALLING_SUPPORTED_ANTHROPIC_MODELS,
    TOOL_CALLING_UNSUPPORTED_ANTHROPIC_MODELS,
)
from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import BoolInput, DropdownInput, IntInput, MessageTextInput, SecretStrInput, SliderInput
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict


class AnthropicModelComponent(LCModelComponent):
    display_name = i18n.t('components.anthropic.anthropic.display_name')
    description = i18n.t('components.anthropic.anthropic.description')
    icon = "Anthropic"
    name = "AnthropicModel"

    ignore: bool = bool(os.getenv("LANGFLOW_IGNORE_COMPONENT", False))

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.anthropic.anthropic.max_tokens.display_name'),
            advanced=True,
            value=4096,
            info=i18n.t('components.anthropic.anthropic.max_tokens.info'),
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.anthropic.anthropic.model_name.display_name'),
            options=ANTHROPIC_MODELS,
            refresh_button=True,
            value=ANTHROPIC_MODELS[0],
            combobox=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.anthropic.anthropic.api_key.display_name'),
            info=i18n.t('components.anthropic.anthropic.api_key.info'),
            value=None,
            required=True,
            real_time_refresh=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.anthropic.anthropic.temperature.display_name'),
            value=0.1,
            info=i18n.t('components.anthropic.anthropic.temperature.info'),
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
        ),
        MessageTextInput(
            name="base_url",
            display_name=i18n.t(
                'components.anthropic.anthropic.base_url.display_name'),
            info=i18n.t('components.anthropic.anthropic.base_url.info'),
            value=DEFAULT_ANTHROPIC_API_URL,
            real_time_refresh=True,
            advanced=True,
        ),
        BoolInput(
            name="tool_model_enabled",
            display_name=i18n.t(
                'components.anthropic.anthropic.tool_model_enabled.display_name'),
            info=i18n.t(
                'components.anthropic.anthropic.tool_model_enabled.info'),
            advanced=False,
            value=False,
            real_time_refresh=True,
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build and return the Anthropic language model."""
        try:
            try:
                from langchain_anthropic.chat_models import ChatAnthropic
            except ImportError as e:
                error_msg = i18n.t(
                    'components.anthropic.anthropic.errors.langchain_anthropic_not_installed')
                raise ImportError(error_msg) from e

            self.status = i18n.t('components.anthropic.anthropic.status.initializing_model',
                                 model=self.model_name)

            try:
                max_tokens_value = getattr(self, "max_tokens", "")
                max_tokens_value = 4096 if max_tokens_value == "" else int(
                    max_tokens_value)

                output = ChatAnthropic(
                    model=self.model_name,
                    anthropic_api_key=self.api_key,
                    max_tokens=max_tokens_value,
                    temperature=self.temperature,
                    anthropic_api_url=self.base_url or DEFAULT_ANTHROPIC_API_URL,
                    streaming=self.stream,
                )

                success_msg = i18n.t('components.anthropic.anthropic.success.model_initialized',
                                     model=self.model_name)
                logger.info(success_msg)
                self.status = success_msg

                return output

            except ValidationError as e:
                error_msg = i18n.t('components.anthropic.anthropic.errors.validation_error',
                                   error=str(e))
                logger.error(error_msg)
                raise
            except Exception as e:
                error_msg = i18n.t(
                    'components.anthropic.anthropic.errors.connection_failed')
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

        except (ImportError, ValueError, ValidationError):
            raise
        except Exception as e:
            error_msg = i18n.t('components.anthropic.anthropic.errors.model_build_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def get_models(self, *, tool_model_enabled: bool | None = None) -> list[str]:
        """Get available Anthropic models.

        Args:
            tool_model_enabled: If True, only return models that support tool calling.

        Returns:
            List of model IDs.
        """
        try:
            self.status = i18n.t(
                'components.anthropic.anthropic.status.fetching_models')

            try:
                import anthropic

                client = anthropic.Anthropic(api_key=self.api_key)
                models = client.models.list(limit=20).data
                model_ids = ANTHROPIC_MODELS + [model.id for model in models]

                logger.debug(i18n.t('components.anthropic.anthropic.logs.models_fetched',
                                    count=len(model_ids)))
            except (ImportError, ValueError, requests.exceptions.RequestException) as e:
                logger.warning(i18n.t('components.anthropic.anthropic.warnings.models_fetch_failed',
                                      error=str(e)))
                model_ids = ANTHROPIC_MODELS

            if tool_model_enabled:
                self.status = i18n.t(
                    'components.anthropic.anthropic.status.filtering_tool_models')

                try:
                    from langchain_anthropic.chat_models import ChatAnthropic
                except ImportError as e:
                    error_msg = i18n.t(
                        'components.anthropic.anthropic.errors.langchain_anthropic_not_installed')
                    raise ImportError(error_msg) from e

                filtered_models = []
                for model in model_ids:
                    if model in TOOL_CALLING_SUPPORTED_ANTHROPIC_MODELS:
                        filtered_models.append(model)
                        logger.debug(i18n.t('components.anthropic.anthropic.logs.tool_model_added',
                                            model=model))
                        continue

                    try:
                        model_with_tool = ChatAnthropic(
                            model=model,
                            anthropic_api_key=self.api_key,
                            anthropic_api_url=cast(
                                "str", self.base_url) or DEFAULT_ANTHROPIC_API_URL,
                        )

                        if (
                            not self.supports_tool_calling(model_with_tool)
                            or model in TOOL_CALLING_UNSUPPORTED_ANTHROPIC_MODELS
                        ):
                            logger.debug(i18n.t('components.anthropic.anthropic.logs.tool_model_skipped',
                                                model=model))
                            continue

                        filtered_models.append(model)
                        logger.debug(i18n.t('components.anthropic.anthropic.logs.tool_model_verified',
                                            model=model))
                    except Exception as e:
                        logger.warning(i18n.t('components.anthropic.anthropic.warnings.tool_check_failed',
                                              model=model, error=str(e)))
                        continue

                logger.info(i18n.t('components.anthropic.anthropic.logs.tool_models_filtered',
                                   count=len(filtered_models)))
                return filtered_models

            return model_ids

        except ImportError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.anthropic.anthropic.errors.get_models_failed',
                               error=str(e))
            logger.exception(error_msg)
            return ANTHROPIC_MODELS

    def _get_exception_message(self, exception: Exception) -> str | None:
        """Get a message from an Anthropic exception.

        Args:
            exception: The exception to get the message from.

        Returns:
            The message from the exception or None.
        """
        try:
            try:
                from anthropic import BadRequestError
            except ImportError:
                logger.debug(
                    i18n.t('components.anthropic.anthropic.logs.anthropic_not_available'))
                return None

            if isinstance(exception, BadRequestError):
                message = exception.body.get("error", {}).get("message")
                if message:
                    logger.debug(i18n.t('components.anthropic.anthropic.logs.extracted_error_message',
                                        message=message))
                    return message
            return None

        except Exception as e:
            logger.warning(i18n.t('components.anthropic.anthropic.warnings.exception_message_extraction_failed',
                                  error=str(e)))
            return None

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        """Update build configuration when fields change."""
        try:
            # Set default base URL if not provided
            if "base_url" in build_config and build_config["base_url"]["value"] is None:
                build_config["base_url"]["value"] = DEFAULT_ANTHROPIC_API_URL
                self.base_url = DEFAULT_ANTHROPIC_API_URL
                logger.debug(
                    i18n.t('components.anthropic.anthropic.logs.default_url_set'))

            # Update model list when relevant fields change
            if field_name in {"base_url", "model_name", "tool_model_enabled", "api_key"} and field_value:
                try:
                    if len(self.api_key) == 0:
                        ids = ANTHROPIC_MODELS
                        logger.debug(
                            i18n.t('components.anthropic.anthropic.logs.using_default_models'))
                    else:
                        try:
                            self.status = i18n.t(
                                'components.anthropic.anthropic.status.updating_models')
                            ids = self.get_models(
                                tool_model_enabled=self.tool_model_enabled)
                            logger.info(i18n.t('components.anthropic.anthropic.logs.models_updated',
                                               count=len(ids)))
                        except (ImportError, ValueError, requests.exceptions.RequestException) as e:
                            logger.warning(i18n.t('components.anthropic.anthropic.warnings.models_update_failed',
                                                  error=str(e)))
                            ids = ANTHROPIC_MODELS

                    build_config.setdefault("model_name", {})
                    build_config["model_name"]["options"] = ids
                    build_config["model_name"].setdefault("value", ids[0])
                    build_config["model_name"]["combobox"] = True

                except Exception as e:
                    error_msg = i18n.t('components.anthropic.anthropic.errors.config_update_failed',
                                       error=str(e))
                    logger.exception(error_msg)
                    raise ValueError(error_msg) from e

            return build_config

        except ValueError:
            raise
        except Exception as e:
            error_msg = i18n.t('components.anthropic.anthropic.errors.build_config_update_failed',
                               error=str(e))
            logger.exception(error_msg)
            return build_config
