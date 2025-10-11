import i18n
import os

from mem0 import Memory, MemoryClient

from lfx.base.memory.model import LCChatMemoryComponent
from lfx.inputs.inputs import DictInput, HandleInput, MessageTextInput, NestedDictInput, SecretStrInput
from lfx.io import Output
from lfx.log.logger import logger
from lfx.schema.data import Data


class Mem0MemoryComponent(LCChatMemoryComponent):
    display_name = i18n.t('components.mem0.mem0_chat_memory.display_name')
    description = i18n.t('components.mem0.mem0_chat_memory.description')
    name = "mem0_chat_memory"
    icon: str = "Mem0"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        NestedDictInput(
            name="mem0_config",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.mem0_config.display_name'),
            info=i18n.t('components.mem0.mem0_chat_memory.mem0_config.info'),
            input_types=["Data"],
        ),
        MessageTextInput(
            name="ingest_message",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.ingest_message.display_name'),
            info=i18n.t(
                'components.mem0.mem0_chat_memory.ingest_message.info'),
        ),
        HandleInput(
            name="existing_memory",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.existing_memory.display_name'),
            input_types=["Memory"],
            info=i18n.t(
                'components.mem0.mem0_chat_memory.existing_memory.info'),
        ),
        MessageTextInput(
            name="user_id",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.user_id.display_name'),
            info=i18n.t('components.mem0.mem0_chat_memory.user_id.info')
        ),
        MessageTextInput(
            name="search_query",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.search_query.display_name'),
            info=i18n.t('components.mem0.mem0_chat_memory.search_query.info')
        ),
        SecretStrInput(
            name="mem0_api_key",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.mem0_api_key.display_name'),
            info=i18n.t('components.mem0.mem0_chat_memory.mem0_api_key.info'),
        ),
        DictInput(
            name="metadata",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.metadata.display_name'),
            info=i18n.t('components.mem0.mem0_chat_memory.metadata.info'),
            advanced=True,
        ),
        SecretStrInput(
            name="openai_api_key",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.openai_api_key.display_name'),
            required=False,
            info=i18n.t(
                'components.mem0.mem0_chat_memory.openai_api_key.info'),
        ),
    ]

    outputs = [
        Output(
            name="memory",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.outputs.memory.display_name'),
            method="ingest_data"
        ),
        Output(
            name="search_results",
            display_name=i18n.t(
                'components.mem0.mem0_chat_memory.outputs.search_results.display_name'),
            method="build_search_results",
        ),
    ]

    def build_mem0(self) -> Memory:
        """Initializes a Mem0 memory instance based on provided configuration and API keys."""
        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key

        try:
            if not self.mem0_api_key:
                return Memory.from_config(config_dict=dict(self.mem0_config)) if self.mem0_config else Memory()
            if self.mem0_config:
                return MemoryClient.from_config(api_key=self.mem0_api_key, config_dict=dict(self.mem0_config))
            return MemoryClient(api_key=self.mem0_api_key)
        except ImportError as e:
            msg = "Mem0 is not properly installed. Please install it with 'pip install -U mem0ai'."
            raise ImportError(msg) from e

    def ingest_data(self) -> Memory:
        """Ingests a new message into Mem0 memory and returns the updated memory instance."""
        mem0_memory = self.existing_memory or self.build_mem0()

        if not self.ingest_message or not self.user_id:
            logger.warning(
                "Missing 'ingest_message' or 'user_id'; cannot ingest data.")
            return mem0_memory

        metadata = self.metadata or {}

        logger.info("Ingesting message for user_id: %s", self.user_id)

        try:
            mem0_memory.add(self.ingest_message,
                            user_id=self.user_id, metadata=metadata)
        except Exception:
            logger.exception("Failed to add message to Mem0 memory.")
            raise

        return mem0_memory

    def build_search_results(self) -> Data:
        """Searches the Mem0 memory for related messages based on the search query and returns the results."""
        mem0_memory = self.ingest_data()
        search_query = self.search_query
        user_id = self.user_id

        logger.info("Search query: %s", search_query)

        try:
            if search_query:
                logger.info("Performing search with query.")
                related_memories = mem0_memory.search(
                    query=search_query, user_id=user_id)
            else:
                logger.info("Retrieving all memories for user_id: %s", user_id)
                related_memories = mem0_memory.get_all(user_id=user_id)
        except Exception:
            logger.exception("Failed to retrieve related memories from Mem0.")
            raise

        logger.info("Related memories retrieved: %s", related_memories)
        return related_memories
