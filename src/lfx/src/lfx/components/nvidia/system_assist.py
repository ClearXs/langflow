import os
import i18n
import asyncio

from lfx.custom.custom_component.component_with_cache import ComponentWithCache
from lfx.io import MessageTextInput, Output
from lfx.schema import Message
from lfx.services.cache.utils import CacheMiss

RISE_INITIALIZED_KEY = "rise_initialized"


class NvidiaSystemAssistComponent(ComponentWithCache):
    display_name = i18n.t('components.nvidia.system_assist.display_name')
    description = i18n.t('components.nvidia.system_assist.description')
    documentation = "https://docs.langflow.org/integrations-nvidia-g-assist"
    icon = "NVIDIA"
    rise_initialized = False

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="prompt",
            display_name=i18n.t(
                'components.nvidia.system_assist.prompt.display_name'),
            info=i18n.t('components.nvidia.system_assist.prompt.info'),
            value="",
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.nvidia.system_assist.outputs.response.display_name'),
            name="response",
            method="sys_assist_prompt"
        ),
    ]

    def maybe_register_rise_client(self):
        try:
            from gassist.rise import register_rise_client

            rise_initialized = self._shared_component_cache.get(
                RISE_INITIALIZED_KEY)
            if not isinstance(rise_initialized, CacheMiss) and rise_initialized:
                return
            self.log("Initializing Rise Client")

            register_rise_client()
            self._shared_component_cache.set(
                key=RISE_INITIALIZED_KEY, value=True)
        except ImportError as e:
            msg = "NVIDIA System-Assist is Windows only and not supported on this platform"
            raise ValueError(msg) from e
        except Exception as e:
            msg = f"An error occurred initializing NVIDIA System-Assist: {e}"
            raise ValueError(msg) from e

    async def sys_assist_prompt(self) -> Message:
        try:
            from gassist.rise import send_rise_command
        except ImportError as e:
            msg = "NVIDIA System-Assist is Windows only and not supported on this platform"
            raise ValueError(msg) from e

        self.maybe_register_rise_client()

        response = await asyncio.to_thread(send_rise_command, self.prompt)

        return Message(text=response["completed_response"]) if response is not None else Message(text=None)
