import os
import i18n
from typing import Any
from urllib.parse import urljoin

import httpx

from lfx.base.embeddings.model import LCEmbeddingsModel
from lfx.field_typing import Embeddings
from lfx.inputs.inputs import DropdownInput, SecretStrInput
from lfx.io import FloatInput, MessageTextInput


class LMStudioEmbeddingsComponent(LCEmbeddingsModel):
    display_name: str = i18n.t(
        'components.lmstudio.lmstudioembeddings.display_name')
    description: str = i18n.t(
        'components.lmstudio.lmstudioembeddings.description')
    icon = "LMStudio"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    async def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None):  # noqa: ARG002
        if field_name == "model":
            base_url_dict = build_config.get("base_url", {})
            base_url_load_from_db = base_url_dict.get("load_from_db", False)
            base_url_value = base_url_dict.get("value")
            if base_url_load_from_db:
                base_url_value = await self.get_variables(base_url_value, field_name)
            elif not base_url_value:
                base_url_value = "http://localhost:1234/v1"
            build_config["model"]["options"] = await self.get_model(base_url_value)

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
        DropdownInput(
            name="model",
            display_name=i18n.t(
                'components.lmstudio.lmstudioembeddings.model.display_name'),
            advanced=False,
            refresh_button=True,
            required=True,
            info=i18n.t('components.lmstudio.lmstudioembeddings.model.info'),
        ),
        MessageTextInput(
            name="base_url",
            display_name=i18n.t(
                'components.lmstudio.lmstudioembeddings.base_url.display_name'),
            refresh_button=True,
            value="http://localhost:1234/v1",
            required=True,
            info=i18n.t(
                'components.lmstudio.lmstudioembeddings.base_url.info'),
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t(
                'components.lmstudio.lmstudioembeddings.api_key.display_name'),
            advanced=True,
            value="LMSTUDIO_API_KEY",
            info=i18n.t('components.lmstudio.lmstudioembeddings.api_key.info'),
        ),
        FloatInput(
            name="temperature",
            display_name=i18n.t(
                'components.lmstudio.lmstudioembeddings.temperature.display_name'),
            value=0.1,
            advanced=True,
            info=i18n.t(
                'components.lmstudio.lmstudioembeddings.temperature.info'),
        ),
    ]

    def build_embeddings(self) -> Embeddings:
        try:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
        except ImportError as e:
            msg = "Please install langchain-nvidia-ai-endpoints to use LM Studio Embeddings."
            raise ImportError(msg) from e
        try:
            output = NVIDIAEmbeddings(
                model=self.model,
                base_url=self.base_url,
                temperature=self.temperature,
                nvidia_api_key=self.api_key,
            )
        except Exception as e:
            msg = f"Could not connect to LM Studio API. Error: {e}"
            raise ValueError(msg) from e
        return output
