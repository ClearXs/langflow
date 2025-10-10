import i18n
from lfx.base.memory.model import LCChatMemoryComponent
from lfx.field_typing.constants import Memory
from lfx.inputs.inputs import DropdownInput, MessageTextInput, SecretStrInput


class ZepChatMemory(LCChatMemoryComponent):
    display_name = i18n.t('components.zep.zep.display_name')
    description = i18n.t('components.zep.zep.description')
    name = "ZepChatMemory"
    icon = "ZepMemory"
    legacy = True
    replacement = ["helpers.Memory"]

    inputs = [
        MessageTextInput(
            name="url",
            display_name=i18n.t('components.zep.zep.url.display_name'),
            info=i18n.t('components.zep.zep.url.info')
        ),
        SecretStrInput(
            name="api_key",
            display_name=i18n.t('components.zep.zep.api_key.display_name'),
            info=i18n.t('components.zep.zep.api_key.info')
        ),
        DropdownInput(
            name="api_base_path",
            display_name=i18n.t(
                'components.zep.zep.api_base_path.display_name'),
            options=["api/v1", "api/v2"],
            value="api/v1",
            advanced=True,
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t('components.zep.zep.session_id.display_name'),
            info=i18n.t('components.zep.zep.session_id.info'),
            advanced=True
        ),
    ]

    def build_message_history(self) -> Memory:
        try:
            # Monkeypatch API_BASE_PATH to
            # avoid 404
            # This is a workaround for the local Zep instance
            # cloud Zep works with v2
            import zep_python.zep_client
            from zep_python import ZepClient
            from zep_python.langchain import ZepChatMessageHistory

            zep_python.zep_client.API_BASE_PATH = self.api_base_path
        except ImportError as e:
            msg = "Could not import zep-python package. Please install it with `pip install zep-python`."
            raise ImportError(msg) from e

        zep_client = ZepClient(api_url=self.url, api_key=self.api_key)
        return ZepChatMessageHistory(session_id=self.session_id, zep_client=zep_client)
