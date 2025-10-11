import os
import i18n
from typing import Any
from urllib.parse import urljoin

import httpx
from langchain_openai import ChatOpenAI
from typing_extensions import override

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import DictInput, DropdownInput, FloatInput, IntInput, SecretStrInput, StrInput


class LMStudioModelComponent(LCModelComponent):
    display_name = i18n.t('components.lmstudio.lmstudiomodel.display_name')
    description = i18n.t('components.lmstudio.lmstudiomodel.description')
    icon = "LMStudio"
    name = "LMStudioModel"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    @override
    async def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None):
        if field_name == "model_name":
            base_url_dict = build_config.get("base_url", {})
            base_url_load_from_db = base_url_dict.get("load_from_db", False)
            base_url_value = base_url_dict.get("value")
            if base_url_load_from_db:
                base_url_value = await self.get_variables(base_url_value, field_name)
            elif not base_url_value:
                base_url_value = "http://localhost:1234/v1"
            build_config["model_name"]["options"] = await self.get_model(base_url_value)

        return build_config

    @staticmethod
    async def get_model(base_url_value: str) -> list[str]:
        try:
            url = urljoin(base_url_value, "/v1/models")
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                return [model["id"] for model in data.get("data", [])]
        except Exception as e:
            msg = "Could not retrieve models. Please, make sure the LM Studio server is running."
            raise ValueError(msg) from e

    inputs = [
        *LCModelComponent.get_base_inputs(),
        IntInput(
            name="max_tokens",
            display_name=i18n.t(
                'components.lmstudio.lmstudiomodel.max_tokens.display_name'),
            advanced=True,
            info=i18n.t('components.lmstudio.lmstudiomodel.max_tokens.info'),
            range_spec=RangeSpec(min=0, max=128000),
        ),
        DictInput(
            name="model_kwargs",
            display_name=i18n.t(
                'components.lmstudio.lmstudiomodel.model_kwargs.display_name'),
            advanced=True
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.lmstudio.lmstudiomodel.model_name.display_name'),
            advanced=False,
            refresh_button=True,
        ),
        StrInput(
            name="base_url",
            display_name=i18n.t(
                'components.lmstudio.lmstudiomodel.base_url.display_name'),
            advanced=False,
            info=i18n.t('components.lmstudio.lmstudiomodel.base_url.info'),
            value="http://localhost:1234/v1",
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.lmstudio.lmstudiomodel.api_key.display_name'),
            info=i18n.t('components.lmstudio.lmstudiomodel.api_key.info'),
            advanced=True,
            value="LMSTUDIO_API_KEY",
        ),
        FloatInput(
            name="temperature",
            display_name=i18n.t(
                'components.lmstudio.lmstudiomodel.temperature.display_name'),
            value=0.1,
            advanced=True,
        ),
        IntInput(
            name="seed",
            display_name=i18n.t(
                'components.lmstudio.lmstudiomodel.seed.display_name'),
            info=i18n.t('components.lmstudio.lmstudiomodel.seed.info'),
            advanced=True,
            value=1,
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        lmstudio_api_key = self.api_key
        temperature = self.temperature
        model_name: str = self.model_name
        max_tokens = self.max_tokens
        model_kwargs = self.model_kwargs or {}
        base_url = self.base_url or "http://localhost:1234/v1"
        seed = self.seed

        return ChatOpenAI(
            max_tokens=max_tokens or None,
            model_kwargs=model_kwargs,
            model=model_name,
            base_url=base_url,
            api_key=lmstudio_api_key,
            temperature=temperature if temperature is not None else 0.1,
            seed=seed,
        )

    def _get_exception_message(self, e: Exception):
        """Get a message from an LM Studio exception.

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
