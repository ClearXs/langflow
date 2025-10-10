import i18n
import requests
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr
from typing_extensions import override

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import (
    BoolInput,
    DictInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
    SliderInput,
)

XAI_DEFAULT_MODELS = ["grok-2-latest"]


class XAIModelComponent(LCModelComponent):
    display_name = i18n.t('components.xai.xai.display_name')
    description = i18n.t('components.xai.xai.description')
    icon = "xAI"
    name = "xAIModel"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_tokens",
            display_name=i18n.t('components.xai.xai.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.xai.xai.max_tokens.info'),
            range_spec=RangeSpec(min=0, max=128000),
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.xai.xai.model_kwargs.display_name'),
            advanced=True,
            info=i18n.t('components.xai.xai.model_kwargs.info'),
        ),
        BoolInput(
            name="json_mode",
            display_name=i18n.t('components.xai.xai.json_mode.display_name'),
            advanced=True,
            info=i18n.t('components.xai.xai.json_mode.info'),
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t('components.xai.xai.model_name.display_name'),
            advanced=False,
            options=XAI_DEFAULT_MODELS,
            value=XAI_DEFAULT_MODELS[0],
            refresh_button=True,
            combobox=True,
            info=i18n.t('components.xai.xai.model_name.info'),
        ),
        MessageTextInput(
            name="base_url",
            display_name=i18n.t('components.xai.xai.base_url.display_name'),
            advanced=True,
            info=i18n.t('components.xai.xai.base_url.info'),
            value="https://api.x.ai/v1",
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t('components.xai.xai.api_key.display_name'),
            info=i18n.t('components.xai.xai.api_key.info'),
            advanced=False,
            value="XAI_API_KEY",
            required=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t('components.xai.xai.temperature.display_name'),
            value=0.1,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            advanced=True,
        ),
        IntInput(
            name="seed",
            display_name=i18n.t('components.xai.xai.seed.display_name'),
            info=i18n.t('components.xai.xai.seed.info'),
            advanced=True,
            value=1,
        ),
    ]

    def get_models(self) -> list[str]:
        """Fetch available models from xAI API."""
        if not self.api_key:
            return XAI_DEFAULT_MODELS

        base_url = self.base_url or "https://api.x.ai/v1"
        url = f"{base_url}/language-models"
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Accept": "application/json"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract model IDs and any aliases
            models = set()
            for model in data.get("models", []):
                models.add(model["id"])
                models.update(model.get("aliases", []))

            return sorted(models) if models else XAI_DEFAULT_MODELS
        except requests.RequestException as e:
            self.status = f"Error fetching models: {e}"
            return XAI_DEFAULT_MODELS

    @override
    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        """Update build configuration with fresh model list when key fields change."""
        if field_name in {"api_key", "base_url", "model_name"}:
            models = self.get_models()
            build_config["model_name"]["options"] = models
        return build_config

    def build_model(self) -> LanguageModel:
        api_key = self.api_key
        temperature = self.temperature
        model_name: str = self.model_name
        max_tokens = self.max_tokens
        model_kwargs = self.model_kwargs or {}
        base_url = self.base_url or "https://api.x.ai/v1"
        json_mode = self.json_mode
        seed = self.seed

        api_key = SecretStr(api_key).get_secret_value() if api_key else None

        output = ChatOpenAI(
            max_tokens=max_tokens or None,
            model_kwargs=model_kwargs,
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature if temperature is not None else 0.1,
            seed=seed,
        )

        if json_mode:
            output = output.bind(response_format={"type": "json_object"})

        return output

    def _get_exception_message(self, e: Exception):
        """Get a message from an xAI exception.

        Args:
            e (Exception): The exception to get the message from.

        Returns:
            str: The message from the exception.
        """
        try:
            from openai import BadRequestError
        except ImportError:
            return None
        if isinstance(e, BadRequestError):
            message = e.body.get("message")
            if message:
                return message
        return None
