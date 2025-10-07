from typing import Any
import i18n

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from lfx.base.models.anthropic_constants import ANTHROPIC_MODELS
from lfx.base.models.google_generative_ai_constants import GOOGLE_GENERATIVE_AI_MODELS
from lfx.base.models.model import LCModelComponent
from lfx.base.models.openai_constants import OPENAI_CHAT_MODEL_NAMES, OPENAI_REASONING_MODEL_NAMES
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import BoolInput
from lfx.io import DropdownInput, MessageInput, MultilineInput, SecretStrInput, SliderInput
from lfx.schema.dotdict import dotdict


class LanguageModelComponent(LCModelComponent):
    display_name = i18n.t('components.models.language_model.display_name')
    description = i18n.t('components.models.language_model.description')
    documentation: str = "https://docs.langflow.org/components-models"
    icon = "brain-circuit"
    category = "models"
    priority = 0  # Set priority to 0 to make it appear first

    inputs = [
        DropdownInput(
            name="provider",
            display_name=i18n.t(
                'components.models.language_model.provider.display_name'),
            options=["OpenAI", "Anthropic", "Google"],
            value="OpenAI",
            info=i18n.t('components.models.language_model.provider.info'),
            real_time_refresh=True,
            options_metadata=[{"icon": "OpenAI"}, {
                "icon": "Anthropic"}, {"icon": "GoogleGenerativeAI"}],
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.models.language_model.model_name.display_name'),
            options=OPENAI_CHAT_MODEL_NAMES + OPENAI_REASONING_MODEL_NAMES,
            value=OPENAI_CHAT_MODEL_NAMES[0],
            info=i18n.t('components.models.language_model.model_name.info'),
            real_time_refresh=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.models.language_model.api_key.openai_display_name'),
            info=i18n.t('components.models.language_model.api_key.info'),
            required=False,
            show=True,
            real_time_refresh=True,
        ),
        MessageInput(
            name="input_value",
            display_name=i18n.t(
                'components.models.language_model.input_value.display_name'),
            info=i18n.t('components.models.language_model.input_value.info'),
        ),
        MultilineInput(
            name="system_message",
            display_name=i18n.t(
                'components.models.language_model.system_message.display_name'),
            info=i18n.t(
                'components.models.language_model.system_message.info'),
            advanced=False,
        ),
        BoolInput(
            name="stream",
            display_name=i18n.t(
                'components.models.language_model.stream.display_name'),
            info=i18n.t('components.models.language_model.stream.info'),
            value=False,
            advanced=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.models.language_model.temperature.display_name'),
            value=0.1,
            info=i18n.t('components.models.language_model.temperature.info'),
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
        ),
    ]

    def build_model(self) -> LanguageModel:
        provider = self.provider
        model_name = self.model_name
        temperature = self.temperature
        stream = self.stream

        try:
            if provider == "OpenAI":
                if not self.api_key:
                    error_message = i18n.t(
                        'components.models.language_model.errors.openai_api_key_required')
                    self.status = error_message
                    raise ValueError(error_message)

                if model_name in OPENAI_REASONING_MODEL_NAMES:
                    # reasoning models do not support temperature (yet)
                    temperature = None
                    info_message = i18n.t('components.models.language_model.info.reasoning_model_no_temperature',
                                          model=model_name)
                    self.status = info_message

                success_message = i18n.t('components.models.language_model.success.openai_model_created',
                                         model=model_name)
                self.status = success_message

                return ChatOpenAI(
                    model_name=model_name,
                    temperature=temperature,
                    streaming=stream,
                    openai_api_key=self.api_key,
                )

            elif provider == "Anthropic":
                if not self.api_key:
                    error_message = i18n.t(
                        'components.models.language_model.errors.anthropic_api_key_required')
                    self.status = error_message
                    raise ValueError(error_message)

                success_message = i18n.t('components.models.language_model.success.anthropic_model_created',
                                         model=model_name)
                self.status = success_message

                return ChatAnthropic(
                    model=model_name,
                    temperature=temperature,
                    streaming=stream,
                    anthropic_api_key=self.api_key,
                )

            elif provider == "Google":
                if not self.api_key:
                    error_message = i18n.t(
                        'components.models.language_model.errors.google_api_key_required')
                    self.status = error_message
                    raise ValueError(error_message)

                success_message = i18n.t('components.models.language_model.success.google_model_created',
                                         model=model_name)
                self.status = success_message

                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=temperature,
                    streaming=stream,
                    google_api_key=self.api_key,
                )
            else:
                error_message = i18n.t('components.models.language_model.errors.unknown_provider',
                                       provider=provider)
                self.status = error_message
                raise ValueError(error_message)

        except Exception as e:
            error_message = i18n.t('components.models.language_model.errors.model_creation_failed',
                                   provider=provider, error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None) -> dotdict:
        if field_name == "provider":
            if field_value == "OpenAI":
                build_config["model_name"]["options"] = OPENAI_CHAT_MODEL_NAMES + \
                    OPENAI_REASONING_MODEL_NAMES
                build_config["model_name"]["value"] = OPENAI_CHAT_MODEL_NAMES[0]
                build_config["api_key"]["display_name"] = i18n.t(
                    'components.models.language_model.api_key.openai_display_name')
            elif field_value == "Anthropic":
                build_config["model_name"]["options"] = ANTHROPIC_MODELS
                build_config["model_name"]["value"] = ANTHROPIC_MODELS[0]
                build_config["api_key"]["display_name"] = i18n.t(
                    'components.models.language_model.api_key.anthropic_display_name')
            elif field_value == "Google":
                build_config["model_name"]["options"] = GOOGLE_GENERATIVE_AI_MODELS
                build_config["model_name"]["value"] = GOOGLE_GENERATIVE_AI_MODELS[0]
                build_config["api_key"]["display_name"] = i18n.t(
                    'components.models.language_model.api_key.google_display_name')

        elif field_name == "model_name" and field_value.startswith("o1") and self.provider == "OpenAI":
            # Hide system_message for o1 models - currently unsupported
            if "system_message" in build_config:
                build_config["system_message"]["show"] = False
                # Set info about o1 models not supporting system messages
                build_config["system_message"]["info"] = i18n.t(
                    'components.models.language_model.system_message.o1_not_supported')

        elif field_name == "model_name" and not field_value.startswith("o1") and "system_message" in build_config:
            build_config["system_message"]["show"] = True
            build_config["system_message"]["info"] = i18n.t(
                'components.models.language_model.system_message.info')

        return build_config
