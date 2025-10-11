import i18n
import asyncio
from typing import Any
from urllib.parse import urljoin

import httpx
from langchain_ollama import ChatOllama

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.io import BoolInput, DictInput, DropdownInput, FloatInput, IntInput, MessageTextInput, SliderInput
from lfx.log.logger import logger
from lfx.utils.util import transform_localhost_url

HTTP_STATUS_OK = 200


class ChatOllamaComponent(LCModelComponent):
    display_name = i18n.t('components.ollama.ollama.display_name')
    description = i18n.t('components.ollama.ollama.description')
    icon = "Ollama"
    name = "OllamaModel"

    # Define constants for JSON keys
    JSON_MODELS_KEY = "models"
    JSON_NAME_KEY = "name"
    JSON_CAPABILITIES_KEY = "capabilities"
    DESIRED_CAPABILITY = "completion"
    TOOL_CALLING_CAPABILITY = "tools"

    inputs = [
        MessageTextInput(
            name="base_url",
            display_name="Base URL",
            info="Endpoint of the Ollama API. Defaults to http://localhost:11434 .",
            value="http://localhost:11434",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="model_name",
            display_name=i18n.t(
                'components.ollama.ollama.model_name.display_name'),
            options=[],
            info=i18n.t('components.ollama.ollama.model_name.info'),
            refresh_button=True,
            real_time_refresh=True,
        ),
        SliderInput(
            name="temperature",
            display_name=i18n.t(
                'components.ollama.ollama.temperature.display_name'),
            value=0.1,
            range_spec=RangeSpec(min=0, max=1, step=0.01),
            advanced=True,
        ),
        MessageTextInput(
            name="format",
            display_name=i18n.t(
                'components.ollama.ollama.format.display_name'),
            info=i18n.t('components.ollama.ollama.format.info'),
            advanced=True
        ),
        DictInput(
            name="metadata",
            display_name=i18n.t(
                'components.ollama.ollama.metadata.display_name'),
            info=i18n.t('components.ollama.ollama.metadata.info'),
            advanced=True
        ),
        DropdownInput(
            name="mirostat",
            display_name=i18n.t(
                'components.ollama.ollama.mirostat.display_name'),
            options=["Disabled", "Mirostat", "Mirostat 2.0"],
            info=i18n.t('components.ollama.ollama.mirostat.info'),
            value="Disabled",
            advanced=True,
            real_time_refresh=True,
        ),
        FloatInput(
            name="mirostat_eta",
            display_name=i18n.t(
                'components.ollama.ollama.mirostat_eta.display_name'),
            info=i18n.t('components.ollama.ollama.mirostat_eta.info'),
            advanced=True,
        ),
        FloatInput(
            name="mirostat_tau",
            display_name=i18n.t(
                'components.ollama.ollama.mirostat_tau.display_name'),
            info=i18n.t('components.ollama.ollama.mirostat_tau.info'),
            advanced=True,
        ),
        IntInput(
            name="num_ctx",
            display_name=i18n.t(
                'components.ollama.ollama.num_ctx.display_name'),
            info=i18n.t('components.ollama.ollama.num_ctx.info'),
            advanced=True,
        ),
        IntInput(
            name="num_gpu",
            display_name=i18n.t(
                'components.ollama.ollama.num_gpu.display_name'),
            info=i18n.t('components.ollama.ollama.num_gpu.info'),
            advanced=True,
        ),
        IntInput(
            name="num_thread",
            display_name=i18n.t(
                'components.ollama.ollama.num_thread.display_name'),
            info=i18n.t('components.ollama.ollama.num_thread.info'),
            advanced=True,
        ),
        IntInput(
            name="repeat_last_n",
            display_name=i18n.t(
                'components.ollama.ollama.repeat_last_n.display_name'),
            info=i18n.t('components.ollama.ollama.repeat_last_n.info'),
            advanced=True,
        ),
        FloatInput(
            name="repeat_penalty",
            display_name=i18n.t(
                'components.ollama.ollama.repeat_penalty.display_name'),
            info=i18n.t('components.ollama.ollama.repeat_penalty.info'),
            advanced=True,
        ),
        FloatInput(
            name="tfs_z",
            display_name=i18n.t('components.ollama.ollama.tfs_z.display_name'),
            info=i18n.t('components.ollama.ollama.tfs_z.info'),
            advanced=True
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.ollama.ollama.timeout.display_name'),
            info=i18n.t('components.ollama.ollama.timeout.info'),
            advanced=True
        ),
        IntInput(
            name="top_k",
            display_name=i18n.t('components.ollama.ollama.top_k.display_name'),
            info=i18n.t('components.ollama.ollama.top_k.info'),
            advanced=True
        ),
        FloatInput(
            name="top_p",
            display_name=i18n.t('components.ollama.ollama.top_p.display_name'),
            info=i18n.t('components.ollama.ollama.top_p.info'),
            advanced=True
        ),
        BoolInput(
            name="verbose",
            display_name=i18n.t(
                'components.ollama.ollama.verbose.display_name'),
            info=i18n.t('components.ollama.ollama.verbose.info'),
            advanced=True
        ),
        MessageTextInput(
            name="tags",
            display_name=i18n.t('components.ollama.ollama.tags.display_name'),
            info=i18n.t('components.ollama.ollama.tags.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="stop_tokens",
            display_name=i18n.t(
                'components.ollama.ollama.stop_tokens.display_name'),
            info=i18n.t('components.ollama.ollama.stop_tokens.info'),
            advanced=True,
        ),
        MessageTextInput(
            name="system",
            display_name=i18n.t(
                'components.ollama.ollama.system.display_name'),
            info=i18n.t('components.ollama.ollama.system.info'),
            advanced=True
        ),
        BoolInput(
            name="tool_model_enabled",
            display_name=i18n.t(
                'components.ollama.ollama.tool_model_enabled.display_name'),
            info=i18n.t('components.ollama.ollama.tool_model_enabled.info'),
            value=True,
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="template",
            display_name=i18n.t(
                'components.ollama.ollama.template.display_name'),
            info=i18n.t('components.ollama.ollama.template.info'),
            advanced=True
        ),
        *LCModelComponent.get_base_inputs(),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        # Mapping mirostat settings to their corresponding values
        mirostat_options = {"Mirostat": 1, "Mirostat 2.0": 2}

        # Default to 0 for 'Disabled'
        mirostat_value = mirostat_options.get(self.mirostat, 0)

        # Set mirostat_eta and mirostat_tau to None if mirostat is disabled
        if mirostat_value == 0:
            mirostat_eta = None
            mirostat_tau = None
        else:
            mirostat_eta = self.mirostat_eta
            mirostat_tau = self.mirostat_tau

        transformed_base_url = transform_localhost_url(self.base_url)

        # Check if URL contains /v1 suffix (OpenAI-compatible mode)
        if transformed_base_url and transformed_base_url.rstrip("/").endswith("/v1"):
            # Strip /v1 suffix and log warning
            transformed_base_url = transformed_base_url.rstrip(
                "/").removesuffix("/v1")
            logger.warning(
                "Detected '/v1' suffix in base URL. The Ollama component uses the native Ollama API, "
                "not the OpenAI-compatible API. The '/v1' suffix has been automatically removed. "
                "If you want to use the OpenAI-compatible API, please use the OpenAI component instead. "
                "Learn more at https://docs.ollama.com/openai#openai-compatibility"
            )

        # Mapping system settings to their corresponding values
        llm_params = {
            "base_url": transformed_base_url,
            "model": self.model_name,
            "mirostat": mirostat_value,
            "format": self.format,
            "metadata": self.metadata,
            "tags": self.tags.split(",") if self.tags else None,
            "mirostat_eta": mirostat_eta,
            "mirostat_tau": mirostat_tau,
            "num_ctx": self.num_ctx or None,
            "num_gpu": self.num_gpu or None,
            "num_thread": self.num_thread or None,
            "repeat_last_n": self.repeat_last_n or None,
            "repeat_penalty": self.repeat_penalty or None,
            "temperature": self.temperature or None,
            "stop": self.stop_tokens.split(",") if self.stop_tokens else None,
            "system": self.system,
            "tfs_z": self.tfs_z or None,
            "timeout": self.timeout or None,
            "top_k": self.top_k or None,
            "top_p": self.top_p or None,
            "verbose": self.verbose,
            "template": self.template,
        }

        # Remove parameters with None values
        llm_params = {k: v for k, v in llm_params.items() if v is not None}

        try:
            output = ChatOllama(**llm_params)
        except Exception as e:
            msg = (
                "Unable to connect to the Ollama API. "
                "Please verify the base URL, ensure the relevant Ollama model is pulled, and try again."
            )
            raise ValueError(msg) from e

        return output

    async def is_valid_ollama_url(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                url = transform_localhost_url(url)
                if not url:
                    return False
                # Strip /v1 suffix if present, as Ollama API endpoints are at root level
                url = url.rstrip("/").removesuffix("/v1")
                if not url.endswith("/"):
                    url = url + "/"
                return (await client.get(urljoin(url, "api/tags"))).status_code == HTTP_STATUS_OK
        except httpx.RequestError:
            return False

    async def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None):
        if field_name == "mirostat":
            if field_value == "Disabled":
                build_config["mirostat_eta"]["advanced"] = True
                build_config["mirostat_tau"]["advanced"] = True
                build_config["mirostat_eta"]["value"] = None
                build_config["mirostat_tau"]["value"] = None

            else:
                build_config["mirostat_eta"]["advanced"] = False
                build_config["mirostat_tau"]["advanced"] = False

                if field_value == "Mirostat 2.0":
                    build_config["mirostat_eta"]["value"] = 0.2
                    build_config["mirostat_tau"]["value"] = 10
                else:
                    build_config["mirostat_eta"]["value"] = 0.1
                    build_config["mirostat_tau"]["value"] = 5

        if field_name in {"model_name", "base_url", "tool_model_enabled"}:
            if await self.is_valid_ollama_url(self.base_url):
                tool_model_enabled = build_config["tool_model_enabled"].get(
                    "value", False) or self.tool_model_enabled
                build_config["model_name"]["options"] = await self.get_models(
                    self.base_url, tool_model_enabled=tool_model_enabled
                )
            else:
                build_config["model_name"]["options"] = []
        if field_name == "keep_alive_flag":
            if field_value == "Keep":
                build_config["keep_alive"]["value"] = "-1"
                build_config["keep_alive"]["advanced"] = True
            elif field_value == "Immediately":
                build_config["keep_alive"]["value"] = "0"
                build_config["keep_alive"]["advanced"] = True
            else:
                build_config["keep_alive"]["advanced"] = False

        return build_config

    async def get_models(self, base_url_value: str, *, tool_model_enabled: bool | None = None) -> list[str]:
        """Fetches a list of models from the Ollama API that do not have the "embedding" capability.

        Args:
            base_url_value (str): The base URL of the Ollama API.
            tool_model_enabled (bool | None, optional): If True, filters the models further to include
                only those that support tool calling. Defaults to None.

        Returns:
            list[str]: A list of model names that do not have the "embedding" capability. If
                `tool_model_enabled` is True, only models supporting tool calling are included.

        Raises:
            ValueError: If there is an issue with the API request or response, or if the model
                names cannot be retrieved.
        """
        try:
            # Strip /v1 suffix if present, as Ollama API endpoints are at root level
            base_url = base_url_value.rstrip("/").removesuffix("/v1")
            if not base_url.endswith("/"):
                base_url = base_url + "/"
            base_url = transform_localhost_url(base_url)

            # Ollama REST API to return models
            tags_url = urljoin(base_url, "api/tags")

            # Ollama REST API to return model capabilities
            show_url = urljoin(base_url, "api/show")

            async with httpx.AsyncClient() as client:
                # Fetch available models
                tags_response = await client.get(tags_url)
                tags_response.raise_for_status()
                models = tags_response.json()
                if asyncio.iscoroutine(models):
                    models = await models
                await logger.adebug(f"Available models: {models}")

                # Filter models that are NOT embedding models
                model_ids = []
                for model in models[self.JSON_MODELS_KEY]:
                    model_name = model[self.JSON_NAME_KEY]
                    await logger.adebug(f"Checking model: {model_name}")

                    payload = {"model": model_name}
                    show_response = await client.post(show_url, json=payload)
                    show_response.raise_for_status()
                    json_data = show_response.json()
                    if asyncio.iscoroutine(json_data):
                        json_data = await json_data
                    capabilities = json_data.get(
                        self.JSON_CAPABILITIES_KEY, [])
                    await logger.adebug(f"Model: {model_name}, Capabilities: {capabilities}")

                    if self.DESIRED_CAPABILITY in capabilities and (
                        not tool_model_enabled or self.TOOL_CALLING_CAPABILITY in capabilities
                    ):
                        model_ids.append(model_name)

        except (httpx.RequestError, ValueError) as e:
            msg = "Could not get model names from Ollama."
            raise ValueError(msg) from e

        return model_ids
