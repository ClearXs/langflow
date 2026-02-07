"""Shared LLM configuration.

This config provides a single prefix (LANGFLOW_LLM_) for LLM and embedding
settings used across ETL and knowledge graph features.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Unified configuration for LLM and embedding providers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LANGFLOW_LLM_",
        extra="ignore",
    )

    # LLM Configuration
    api_key: str | None = None
    base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_max_async: int = 4

    # Embedding Configuration
    embedding_model: str = "openai"  # openai, cohere, sentence-transformers
    embedding_dimension: int = 1536
    embedding_batch_size: int = 32

    # Provider-specific embedding settings
    openai_embedding_model: str = "text-embedding-3-small"
    cohere_api_key: str | None = None
    cohere_embedding_model: str = "embed-english-v3.0"
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    sentence_transformer_device: str = "cpu"  # cpu, cuda


llm_config = LLMConfig()
