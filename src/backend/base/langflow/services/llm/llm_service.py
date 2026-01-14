"""Compatibility wrapper for llm_service imports.

This module provides backward compatibility for SurfSense-style imports.
New code should import directly from langflow.services.llm.service instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langflow.services.llm.service import LLMRole, LLMService

if TYPE_CHECKING:
    from langchain_litellm import ChatLiteLLM
    from sqlmodel.ext.asyncio.session import AsyncSession


async def get_user_long_context_llm(
    session: AsyncSession, user_id: str, space_id: int
) -> ChatLiteLLM | None:
    """Get the document summary LLM for a user's space.

    This is a deprecated wrapper function for backward compatibility with SurfSense code.
    New code should use LLMService.get_document_summary_llm() directly.

    Args:
        session: Database session
        user_id: User ID (unused - LLM preferences are space-level)
        space_id: Space ID

    Returns:
        ChatLiteLLM instance or None if not found
    """
    from langflow.services.deps import get_llm_service

    llm_service = get_llm_service()
    return await llm_service.get_document_summary_llm(session, space_id)


async def validate_llm_config(
    provider: str,
    model_name: str,
    api_key: str,
    api_base: str | None = None,
    custom_provider: str | None = None,
    litellm_params: dict | None = None,
) -> tuple[bool, str]:
    """Validate an LLM configuration by attempting a test API call.

    This is a wrapper function for backward compatibility.
    New code should use LLMService.validate_llm_config() directly.

    Args:
        provider: LLM provider (e.g., 'OPENAI', 'ANTHROPIC')
        model_name: Model identifier
        api_key: API key for the provider
        api_base: Optional custom API base URL
        custom_provider: Optional custom provider string
        litellm_params: Optional additional litellm parameters

    Returns:
        Tuple of (is_valid, error_message)
    """
    from langflow.services.deps import get_llm_service

    llm_service = get_llm_service()
    return await llm_service.validate_llm_config(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        custom_provider=custom_provider,
        litellm_params=litellm_params,
    )


__all__ = [
    "LLMRole",
    "LLMService",
    "get_user_long_context_llm",
    "validate_llm_config",
]
