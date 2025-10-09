import i18n
from langchain_mistralai import ChatMistralAI
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.io import BoolInput, DropdownInput, FloatInput, IntInput, SecretStrInput, StrInput


class MistralAIModelComponent(LCModelComponent):
    display_name = i18n.t('components.mistral.mistral.display_name')
    description = i18n.t('components.mistral.mistral.description')
    icon = "MistralAI"
    name = "MistralModel"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.mistral.mistral.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.mistral.mistral.max_tokens.info'),
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.mistral.mistral.model_name.display_name'),
            advanced=False,
            options=[
                "open-mixtral-8x7b",
                "open-mixtral-8x22b",
                "mistral-small-latest",
                "mistral-medium-latest",
                "mistral-large-latest",
                "codestral-latest",
            ],
            value="codestral-latest",
        ),
        StrInput(
            name="mistral_api_base",
            display_name=i18n.t(
                'components.mistral.mistral.mistral_api_base.display_name'),
            advanced=True,
            info=i18n.t('components.mistral.mistral.mistral_api_base.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.mistral.mistral.api_key.display_name'),
            info=i18n.t('components.mistral.mistral.api_key.info'),
            advanced=False,
            required=True,
            value="MISTRAL_API_KEY",
        ),
        FloatInput(
            name="temperature",
            display_name=i18n.t(
                'components.mistral.mistral.temperature.display_name'),
            value=0.1,
            advanced=True,
        ),
        IntInput(
            name="max_retries",
            display_name=i18n.t(
                'components.mistral.mistral.max_retries.display_name'),
            advanced=True,
            value=5,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.mistral.mistral.timeout.display_name'),
            advanced=True,
            value=60,
        ),
        IntInput(
            name="max_concurrent_requests",
            display_name=i18n.t(
                'components.mistral.mistral.max_concurrent_requests.display_name'),
            advanced=True,
            value=3,
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t(
                'components.mistral.mistral.top_p.display_name'),
            advanced=True,
            value=1,
        ),
        IntInput(
            name="random_seed",
            display_name=i18n.t(
                'components.mistral.mistral.random_seed.display_name'),
            value=1,
            advanced=True,
        ),
        BoolInput(
            name="safe_mode",
            display_name=i18n.t(
                'components.mistral.mistral.safe_mode.display_name'),
            advanced=True,
            value=False,
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        try:
            return ChatMistralAI(
                model_name=self.model_name,
                mistral_api_key=SecretStr(
                    self.api_key).get_secret_value() if self.api_key else None,
                endpoint=self.mistral_api_base or "https://api.mistral.ai/v1",
                max_tokens=self.max_tokens or None,
                temperature=self.temperature,
                max_retries=self.max_retries,
                timeout=self.timeout,
                max_concurrent_requests=self.max_concurrent_requests,
                top_p=self.top_p,
                random_seed=self.random_seed,
                safe_mode=self.safe_mode,
                streaming=self.stream,
            )
        except Exception as e:
            msg = "Could not connect to MistralAI API."
            raise ValueError(msg) from e
