import os
import i18n
from langchain_sambanova import ChatSambaNovaCloud
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.base.models.sambanova_constants import SAMBANOVA_MODEL_NAMES
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import DropdownInput, IntInput, SecretStrInput, SliderInput, StrInput


class SambaNovaComponent(LCModelComponent):
    display_name = i18n.t('components.sambanova.sambanova.display_name')
    description = i18n.t('components.sambanova.sambanova.description')
    documentation = "https://cloud.sambanova.ai/"
    icon = "SambaNova"
    name = "SambaNovaModel"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        *LCModelComponent.get_base_inputs(),
        StrInput(
            name="base_url",
            display_name=i18n.t(
                'components.sambanova.sambanova.base_url.display_name'),
            advanced=True,
            info=i18n.t('components.sambanova.sambanova.base_url.info'),
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.sambanova.sambanova.model_name.display_name'),
            advanced=False,
            options=SAMBANOVA_MODEL_NAMES,
            value=SAMBANOVA_MODEL_NAMES[0],
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.sambanova.sambanova.api_key.display_name'),
            info=i18n.t('components.sambanova.sambanova.api_key.info'),
            advanced=False,
            value="SAMBANOVA_API_KEY",
            required=True,
        ),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.sambanova.sambanova.max_tokens.display_name'),
            advanced=True,
            value=2048,
            info=i18n.t('components.sambanova.sambanova.max_tokens.info'),
        ),
        SliderInput(
            name="top_p",
            display_name=i18n.t(
                'components.sambanova.sambanova.top_p.display_name'),
            advanced=True,
            value=1.0,
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            info=i18n.t('components.sambanova.sambanova.top_p.info'),
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.sambanova.sambanova.temperature.display_name'),
            value=0.1,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            advanced=True,
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        sambanova_url = self.base_url
        sambanova_api_key = self.api_key
        model_name = self.model_name
        max_tokens = self.max_tokens
        top_p = self.top_p
        temperature = self.temperature

        api_key = SecretStr(sambanova_api_key).get_secret_value(
        ) if sambanova_api_key else None

        return ChatSambaNovaCloud(
            model=model_name,
            max_tokens=max_tokens or 1024,
            temperature=temperature or 0.07,
            top_p=top_p,
            sambanova_url=sambanova_url,
            sambanova_api_key=api_key,
        )
