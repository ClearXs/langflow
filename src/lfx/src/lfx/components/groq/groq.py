import i18n
import requests
from pydantic.v1 import SecretStr

from lfx.base.models.groq_constants import GROQ_MODELS, TOOL_CALLING_UNSUPPORTED_GROQ_MODELS, UNSUPPORTED_GROQ_MODELS
from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import BoolInput, DropdownInput, IntInput, MessageTextInput, SecretStrInput, SliderInput
from lfx.log.logger import logger


class GroqModel(LCModelComponent):
    display_name: str = "Groq"
    description: str = i18n.t('components.groq.groq.description')
    icon = "Groq"
    name = "GroqModel"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t('components.groq.groq.api_key.display_name'),
            info=i18n.t('components.groq.groq.api_key.info'),
            real_time_refresh=True
        ),
        MessageTextInput(
            name="base_url",
            display_name=i18n.t('components.groq.groq.base_url.display_name'),
            info=i18n.t('components.groq.groq.base_url.info'),
            advanced=True,
            value="https://api.groq.com",
            real_time_refresh=True,
        ),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.groq.groq.max_tokens.display_name'),
            info=i18n.t('components.groq.groq.max_tokens.info'),
            advanced=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.groq.groq.temperature.display_name'),
            value=0.1,
            info=i18n.t('components.groq.groq.temperature.info'),
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
        ),
        IntInput(
            name="n",
            display_name=i18n.t('components.groq.groq.n.display_name'),
            info=i18n.t('components.groq.groq.n.info'),
            advanced=True,
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.groq.groq.model_name.display_name'),
            info=i18n.t('components.groq.groq.model_name.info'),
            options=GROQ_MODELS,
            value=GROQ_MODELS[0],
            refresh_button=True,
            combobox=True,
        ),
        BoolInput(
            name="tool_model_enabled",
            display_name=i18n.t(
                'components.groq.groq.tool_model_enabled.display_name'),
            info=i18n.t('components.groq.groq.tool_model_enabled.info'),
            advanced=False,
            value=False,
            real_time_refresh=True,
        ),
    ]

    def get_models(self, *, tool_model_enabled: bool | None = None) -> list[str]:
        """Get available Groq models.

        Args:
            tool_model_enabled: If True, filter models that support tool calling.

        Returns:
            list[str]: List of available model IDs.
        """
        logger.debug(i18n.t('components.groq.groq.logs.fetching_models',
                            tool_enabled=tool_model_enabled or False))

        try:
            url = f"{self.base_url}/openai/v1/models"
            headers = {"Authorization": f"Bearer {self.api_key}",
                       "Content-Type": "application/json"}

            logger.debug(i18n.t('components.groq.groq.logs.requesting_models',
                                url=url))

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            model_list = response.json()

            model_ids = [
                model["id"] for model in model_list.get("data", [])
                if model["id"] not in UNSUPPORTED_GROQ_MODELS
            ]

            logger.info(i18n.t('components.groq.groq.logs.models_fetched',
                               count=len(model_ids)))

        except (ImportError, ValueError, requests.exceptions.RequestException) as e:
            logger.exception(i18n.t('components.groq.groq.logs.model_fetch_error',
                                    error=str(e)))
            model_ids = GROQ_MODELS

        if tool_model_enabled:
            logger.debug(
                i18n.t('components.groq.groq.logs.filtering_tool_models'))

            try:
                from langchain_groq import ChatGroq
            except ImportError as e:
                error_msg = i18n.t(
                    'components.groq.groq.errors.langchain_not_installed')
                logger.error(error_msg)
                raise ImportError(error_msg) from e

            filtered_models = []
            for model in model_ids:
                if model in TOOL_CALLING_UNSUPPORTED_GROQ_MODELS:
                    logger.debug(i18n.t('components.groq.groq.logs.model_unsupported',
                                        model=model))
                    continue

                try:
                    model_with_tool = ChatGroq(
                        model=model,
                        api_key=self.api_key,
                        base_url=self.base_url,
                    )
                    if self.supports_tool_calling(model_with_tool):
                        filtered_models.append(model)
                        logger.debug(i18n.t('components.groq.groq.logs.tool_support_confirmed',
                                            model=model))
                    else:
                        logger.debug(i18n.t('components.groq.groq.logs.tool_support_not_found',
                                            model=model))
                except Exception as e:
                    logger.debug(i18n.t('components.groq.groq.logs.tool_check_failed',
                                        model=model,
                                        error=str(e)))

            model_ids = filtered_models
            logger.info(i18n.t('components.groq.groq.logs.tool_models_filtered',
                               count=len(model_ids)))

        return model_ids

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        """Update build configuration when inputs change.

        Args:
            build_config: The build configuration to update.
            field_value: The new field value.
            field_name: The name of the field that changed.

        Returns:
            dict: Updated build configuration.
        """
        if field_name in {"base_url", "model_name", "tool_model_enabled", "api_key"} and field_value:
            logger.debug(i18n.t('components.groq.groq.logs.updating_config',
                                field=field_name))

            try:
                if len(self.api_key) != 0:
                    try:
                        logger.debug(
                            i18n.t('components.groq.groq.logs.fetching_available_models'))
                        ids = self.get_models(
                            tool_model_enabled=self.tool_model_enabled)
                    except (ImportError, ValueError, requests.exceptions.RequestException) as e:
                        logger.exception(i18n.t('components.groq.groq.logs.model_fetch_fallback',
                                                error=str(e)))
                        ids = GROQ_MODELS

                    build_config.setdefault("model_name", {})
                    build_config["model_name"]["options"] = ids
                    build_config["model_name"].setdefault("value", ids[0])

                    logger.debug(i18n.t('components.groq.groq.logs.config_updated',
                                        model_count=len(ids),
                                        default_model=ids[0] if ids else 'none'))

            except Exception as e:
                error_msg = i18n.t('components.groq.groq.errors.config_update_failed',
                                   error=str(e))
                logger.exception(error_msg)
                raise ValueError(error_msg) from e

        return build_config

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        """Build Groq language model.

        Returns:
            LanguageModel: Configured ChatGroq instance.

        Raises:
            ImportError: If langchain-groq package is not installed.
        """
        logger.info(i18n.t('components.groq.groq.logs.building_model',
                           model=self.model_name))

        try:
            from langchain_groq import ChatGroq
        except ImportError as e:
            error_msg = i18n.t(
                'components.groq.groq.errors.package_not_installed')
            logger.error(error_msg)
            raise ImportError(error_msg) from e

        logger.debug(i18n.t('components.groq.groq.logs.model_parameters',
                            max_tokens=self.max_tokens or 'default',
                            temperature=self.temperature,
                            n=self.n or 1,
                            streaming=self.stream))

        model_instance = ChatGroq(
            model=self.model_name,
            max_tokens=self.max_tokens or None,
            temperature=self.temperature,
            base_url=self.base_url,
            n=self.n or 1,
            api_key=SecretStr(self.api_key).get_secret_value(),
            streaming=self.stream,
        )

        logger.info(i18n.t('components.groq.groq.logs.model_built'))
        return model_instance
