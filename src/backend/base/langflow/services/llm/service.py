"""LLMService for managing LLM configurations and instances in Holo knowledge system."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import litellm
from langchain_core.messages import HumanMessage
from langchain_litellm import ChatLiteLLM
from sqlalchemy.future import select

from langflow.services.base import Service
from langflow.services.database.models import LLMConfig, Space

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

    from langflow.services.settings.service import SettingsService

# Configure litellm to automatically drop unsupported parameters
litellm.drop_params = True

logger = logging.getLogger(__name__)


class LLMRole:
    """LLM role definitions for different use cases."""

    AGENT = "agent"  # For agent/chat operations
    DOCUMENT_SUMMARY = "document_summary"  # For document summarization


class LLMService(Service):
    """Service for managing LLM configurations and instances.

    This service handles:
    - LLM configuration validation
    - Global and space-level LLM configurations
    - ChatLiteLLM instance creation for different roles
    - Support for 33+ LLM providers via LiteLLM
    """

    name = "llm_service"

    def __init__(self, settings_service: SettingsService):
        """Initialize LLM service.

        Args:
            settings_service: Settings service for accessing configuration
        """
        super().__init__()
        self.settings_service = settings_service
        self.settings = settings_service.settings
        self._global_configs = None
        self.set_ready()

    def _load_global_configs(self) -> list[dict]:
        """Load global LLM configurations from YAML file.

        Returns:
            List of global LLM configuration dictionaries
        """
        if self._global_configs is not None:
            return self._global_configs

        # TODO: Implement YAML loading from settings.global_llm_config_path
        # For now, return empty list
        self._global_configs = []
        return self._global_configs

    def get_global_llm_config(self, llm_config_id: int) -> dict | None:
        """Get a global LLM configuration by ID.

        Global configs have negative IDs.

        Args:
            llm_config_id: The ID of the global config (should be negative)

        Returns:
            Global config dictionary or None if not found
        """
        if llm_config_id >= 0:
            return None

        global_configs = self._load_global_configs()
        for cfg in global_configs:
            if cfg.get("id") == llm_config_id:
                return cfg

        return None

    def _build_provider_map(self) -> dict[str, str]:
        """Build provider name to litellm prefix mapping.

        Returns:
            Dictionary mapping provider enum values to litellm prefixes
        """
        return {
            "OPENAI": "openai",
            "ANTHROPIC": "anthropic",
            "GROQ": "groq",
            "COHERE": "cohere",
            "GOOGLE": "gemini",
            "OLLAMA": "ollama",
            "MISTRAL": "mistral",
            "AZURE": "azure",
            "OPENROUTER": "openrouter",
            "COMETAPI": "cometapi",
            "XAI": "xai",
            "BEDROCK": "bedrock",
            "VERTEX_AI": "vertex_ai",
            "TOGETHER_AI": "together_ai",
            "FIREWORKS_AI": "fireworks_ai",
            "REPLICATE": "replicate",
            "PERPLEXITY": "perplexity",
            "ANYSCALE": "anyscale",
            "DEEPINFRA": "deepinfra",
            "CEREBRAS": "cerebras",
            "SAMBANOVA": "sambanova",
            "AI21": "ai21",
            "CLOUDFLARE": "cloudflare",
            "DATABRICKS": "databricks",
            "HUGGINGFACE": "huggingface",
            # Chinese LLM providers (use OpenAI-compatible API)
            "DEEPSEEK": "openai",
            "ALIBABA_QWEN": "openai",
            "MOONSHOT": "openai",
            "ZHIPU": "openai",
        }

    def _build_model_string(
        self, provider: str, model_name: str, custom_provider: str | None = None
    ) -> str:
        """Build litellm model string from provider and model name.

        Args:
            provider: Provider name (e.g., 'OPENAI', 'ANTHROPIC')
            model_name: Model identifier
            custom_provider: Optional custom provider prefix

        Returns:
            Litellm-formatted model string (e.g., 'openai/gpt-4')
        """
        if custom_provider:
            return f"{custom_provider}/{model_name}"

        provider_map = self._build_provider_map()
        provider_prefix = provider_map.get(provider, provider.lower())
        return f"{provider_prefix}/{model_name}"

    async def validate_llm_config(
        self,
        provider: str,
        model_name: str,
        api_key: str,
        api_base: str | None = None,
        custom_provider: str | None = None,
        litellm_params: dict | None = None,
    ) -> tuple[bool, str]:
        """Validate an LLM configuration by attempting a test API call.

        Args:
            provider: LLM provider (e.g., 'OPENAI', 'ANTHROPIC')
            model_name: Model identifier
            api_key: API key for the provider
            api_base: Optional custom API base URL
            custom_provider: Optional custom provider string
            litellm_params: Optional additional litellm parameters

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if config works, False otherwise
            - error_message: Empty string if valid, error description if invalid
        """
        try:
            # Build the model string for litellm
            model_string = self._build_model_string(provider, model_name, custom_provider)

            # Create ChatLiteLLM instance
            litellm_kwargs = {
                "model": model_string,
                "api_key": api_key,
                "timeout": 30,  # Set a timeout for validation
            }

            # Add optional parameters
            if api_base:
                litellm_kwargs["api_base"] = api_base

            # Add any additional litellm parameters
            if litellm_params:
                litellm_kwargs.update(litellm_params)

            llm = ChatLiteLLM(**litellm_kwargs)

            # Make a simple test call
            test_message = HumanMessage(content="Hello")
            response = await llm.ainvoke([test_message])

            # If we got here without exception, the config is valid
            if response and response.content:
                logger.info(f"Successfully validated LLM config for model: {model_string}")
                return True, ""
            logger.warning(
                f"LLM config validation returned empty response for model: {model_string}"
            )
            return False, "LLM returned an empty response"

        except Exception as e:
            error_msg = f"Failed to validate LLM configuration: {e!s}"
            logger.error(error_msg)
            return False, error_msg

    async def get_space_llm_instance(
        self, session: AsyncSession, space_id: int, role: str
    ) -> ChatLiteLLM | None:
        """Get a ChatLiteLLM instance for a specific space and role.

        LLM preferences are stored at the space level and shared by all members.

        Args:
            session: Database session
            space_id: Space ID
            role: LLM role ('agent' or 'document_summary')

        Returns:
            ChatLiteLLM instance or None if not found
        """
        try:
            # Get the space with its LLM preferences
            result = await session.execute(select(Space).where(Space.id == space_id))
            space = result.scalars().first()

            if not space:
                logger.error(f"Space {space_id} not found")
                return None

            # Get the appropriate LLM config ID based on role
            llm_config_id = None
            if role == LLMRole.AGENT:
                llm_config_id = space.agent_llm_id
            elif role == LLMRole.DOCUMENT_SUMMARY:
                llm_config_id = space.document_summary_llm_id
            else:
                logger.error(f"Invalid LLM role: {role}")
                return None

            if not llm_config_id:
                logger.error(f"No {role} LLM configured for space {space_id}")
                return None

            # Check if this is a global config (negative ID)
            if llm_config_id < 0:
                global_config = self.get_global_llm_config(llm_config_id)
                if not global_config:
                    logger.error(f"Global LLM config {llm_config_id} not found")
                    return None

                # Build model string for global config
                model_string = self._build_model_string(
                    global_config["provider"],
                    global_config["model_name"],
                    global_config.get("custom_provider"),
                )

                # Create ChatLiteLLM instance from global config
                litellm_kwargs = {
                    "model": model_string,
                    "api_key": global_config["api_key"],
                }

                if global_config.get("api_base"):
                    litellm_kwargs["api_base"] = global_config["api_base"]

                if global_config.get("litellm_params"):
                    litellm_kwargs.update(global_config["litellm_params"])

                return ChatLiteLLM(**litellm_kwargs)

            # Get the LLM configuration from database
            result = await session.execute(
                select(LLMConfig).where(
                    LLMConfig.id == llm_config_id,
                    LLMConfig.search_space_id == space_id,
                )
            )
            llm_config = result.scalars().first()

            if not llm_config:
                logger.error(f"LLM config {llm_config_id} not found in space {space_id}")
                return None

            # Build the model string for litellm
            model_string = self._build_model_string(
                llm_config.provider, llm_config.model_name, llm_config.custom_provider
            )

            # Create ChatLiteLLM instance
            litellm_kwargs = {
                "model": model_string,
                "api_key": llm_config.api_key,
            }

            # Add optional parameters
            if llm_config.api_base:
                litellm_kwargs["api_base"] = llm_config.api_base

            # Add any additional litellm parameters
            if llm_config.litellm_params:
                litellm_kwargs.update(llm_config.litellm_params)

            return ChatLiteLLM(**litellm_kwargs)

        except Exception as e:
            logger.error(f"Error getting LLM instance for space {space_id}, role {role}: {e!s}")
            return None

    async def get_agent_llm(self, session: AsyncSession, space_id: int) -> ChatLiteLLM | None:
        """Get the space's agent LLM instance for chat operations.

        Args:
            session: Database session
            space_id: Space ID

        Returns:
            ChatLiteLLM instance or None if not found
        """
        return await self.get_space_llm_instance(session, space_id, LLMRole.AGENT)

    async def get_document_summary_llm(
        self, session: AsyncSession, space_id: int
    ) -> ChatLiteLLM | None:
        """Get the space's document summary LLM instance.

        Args:
            session: Database session
            space_id: Space ID

        Returns:
            ChatLiteLLM instance or None if not found
        """
        return await self.get_space_llm_instance(session, space_id, LLMRole.DOCUMENT_SUMMARY)


# Helper functions for easy access to LLM service methods
async def get_document_summary_llm(session: AsyncSession, space_id: int) -> ChatLiteLLM | None:
    """Get the space's document summary LLM instance.

    Args:
        session: Database session
        space_id: Space ID

    Returns:
        ChatLiteLLM instance or None if not found
    """
    from langflow.services.deps import get_llm_service

    llm_service = get_llm_service()
    return await llm_service.get_document_summary_llm(session, space_id)
