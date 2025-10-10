import i18n
from urllib import parse

from langchain_community.chat_message_histories.redis import RedisChatMessageHistory

from lfx.base.memory.model import LCChatMemoryComponent
from lfx.field_typing.constants import Memory
from lfx.inputs.inputs import IntInput, MessageTextInput, SecretStrInput, StrInput


class RedisIndexChatMemory(LCChatMemoryComponent):
    display_name = i18n.t('components.redis.redis_chat.display_name')
    description = i18n.t('components.redis.redis_chat.description')
    name = "RedisChatMemory"
    icon = "Redis"

    inputs = [
        StrInput(
            name="host",
            display_name=i18n.t(
                'components.redis.redis_chat.host.display_name'),
            required=True,
            value="localhost",
            info=i18n.t('components.redis.redis_chat.host.info')
        ),
        IntInput(
            name="port",
            display_name=i18n.t(
                'components.redis.redis_chat.port.display_name'),
            required=True,
            value=6379,
            info=i18n.t('components.redis.redis_chat.port.info')
        ),
        StrInput(
            name="database",
            display_name=i18n.t(
                'components.redis.redis_chat.database.display_name'),
            required=True,
            value="0",
            info=i18n.t('components.redis.redis_chat.database.info')
        ),
        MessageTextInput(
            name="username",
            display_name=i18n.t(
                'components.redis.redis_chat.username.display_name'),
            value="",
            info=i18n.t('components.redis.redis_chat.username.info'),
            advanced=True
        ),
        SecretStrInput(
            name="password",
            display_name=i18n.t(
                'components.redis.redis_chat.password.display_name'),
            value="",
            info=i18n.t('components.redis.redis_chat.password.info'),
            advanced=True
        ),
        StrInput(
            name="key_prefix",
            display_name=i18n.t(
                'components.redis.redis_chat.key_prefix.display_name'),
            info=i18n.t('components.redis.redis_chat.key_prefix.info'),
            advanced=True
        ),
        MessageTextInput(
            name="session_id",
            display_name=i18n.t(
                'components.redis.redis_chat.session_id.display_name'),
            info=i18n.t('components.redis.redis_chat.session_id.info'),
            advanced=True
        ),
    ]

    def build_message_history(self) -> Memory:
        kwargs = {}
        password: str | None = self.password
        if self.key_prefix:
            kwargs["key_prefix"] = self.key_prefix
        if password:
            password = parse.quote_plus(password)

        url = f"redis://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        return RedisChatMessageHistory(session_id=self.session_id, url=url, **kwargs)
