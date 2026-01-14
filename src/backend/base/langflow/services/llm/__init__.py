"""LLM service for Holo knowledge system."""

from .factory import LLMServiceFactory
from .service import LLMService

# Import wrapper functions for backward compatibility
from .llm_service import get_user_long_context_llm, validate_llm_config

__all__ = [
    "LLMService",
    "LLMServiceFactory",
    "get_user_long_context_llm",
    "validate_llm_config",
]
