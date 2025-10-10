import i18n
import requests
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr
from typing_extensions import override

from lfx.base.models.model import LCModelComponent
from lfx.base.models.novita_constants import MODEL_NAMES
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import (
    BoolInput,
    DictInput,
    DropdownInput,
    HandleInput,
    IntInput,
    SecretStrInput,
    SliderInput,
)


class NovitaModelComponent(LCModelComponent):
    display_name = i18n.t('components.novita.novita.display_name')
    description = i18n.t('components.novita.novita.description')
    icon = "Novita"
    name = "NovitaModel"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.novita.novita.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.novita.novita.max_tokens.info'),
            range_spec=RangeSpec(min=0, max=128000),
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.novita.novita.model_kwargs.display_name'),
            advanced=True,
            info=i18n.t('components.novita.novita.model_kwargs.info'),
        ),
        BoolInput(
            name="json_mode",
            display_name=i18n.t(
                'components.novita.novita.json_mode.display_name'),
            advanced=True,
            info=i18n.t('components.novita.novita.json_mode.info'),
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.novita.novita.model_name.display_name'),
            advanced=False,
            options=MODEL_NAMES,
            value=MODEL_NAMES[0],
            refresh_button=True,
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.novita.novita.api_key.display_name'),
            info=i18n.t('components.novita.novita.api_key.info'),
            advanced=False,
            value="NOVITA_API_KEY",
            real_time_refresh=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.novita.novita.temperature.display_name'),
            value=0.1,
            range_spec=RangeSpec(min=0, max=1)
        ),
        IntInput(
            name="seed",
            display_name=i18n.t('components.novita.novita.seed.display_name'),
            info=i18n.t('components.novita.novita.seed.info'),
            advanced=True,
            value=1,
        ),
        HandleInput(
            name="output_parser",
            display_name=i18n.t(
                'components.novita.novita.output_parser.display_name'),
            info=i18n.t('components.novita.novita.output_parser.info'),
            advanced=True,
            input_types=["OutputParser"],
        ),
    ]

    def get_models(self) -> list[str]:
        base_url = "https://api.novita.ai/v3/openai"
        url = f"{base_url}/models"

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            model_list = response.json()
            return [model["id"] for model in model_list.get("data", [])]
        except requests.RequestException as e:
            self.status = f"Error fetching models: {e}"
            return MODEL_NAMES

    @override
    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        if field_name in {"api_key", "model_name"}:
            models = self.get_models()
            build_config["model_name"]["options"] = models
        return build_config

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        api_key = self.api_key
        temperature = self.temperature
        model_name: str = self.model_name
        max_tokens = self.max_tokens
        model_kwargs = self.model_kwargs or {}
        json_mode = self.json_mode
        seed = self.seed

        try:
            output = ChatOpenAI(
                model=model_name,
                api_key=(SecretStr(api_key).get_secret_value()
                         if api_key else None),
                max_tokens=max_tokens or None,
                temperature=temperature,
                model_kwargs=model_kwargs,
                streaming=self.stream,
                seed=seed,
                base_url="https://api.novita.ai/v3/openai",
            )
        except Exception as e:
            msg = "Could not connect to Novita API."
            raise ValueError(msg) from e

        if json_mode:
            output = output.bind(response_format={"type": "json_object"})

        return output
