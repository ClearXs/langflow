"""ETL Configuration for document processing.

This module provides configuration for:
- ETL service selection (Unstructured, LlamaCloud, Docling)
- Chunking parameters
- Embedding model configuration
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from langflow.services.llm.config import llm_config


class ETLConfig(BaseSettings):
    """Configuration for ETL document processing."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LANGFLOW_ETL_",
        extra="ignore"
    )

    # ETL Service Selection
    etl_service: str = "unstructured"  # unstructured, llamacloud, docling
    etl_fallback_service: str = "docling"  # Fallback if primary fails

    # Unstructured API Configuration
    unstructured_api_key: str | None = None
    unstructured_api_url: str = "https://api.unstructured.io/general/v0/general"
    unstructured_strategy: str = "auto"  # auto, fast, hi_res
    unstructured_mode: str = "elements"  # elements, paged

    # LlamaCloud Configuration
    llama_cloud_api_key: str | None = None
    llama_cloud_result_type: str = "markdown"  # markdown, text

    # Docling Configuration (local processing)
    docling_enabled: bool = True
    docling_batch_size: int = 10  # Process in batches to avoid memory issues

    # Chunking Configuration
    chunk_size: int = 512
    chunk_overlap: int = 128
    code_chunk_size: int = 512
    code_chunk_overlap: int = 64

    # Embedding Configuration
    embedding_model: str = "openai"  # openai, cohere, sentence-transformers
    embedding_dimension: int = 1536  # Must match Vector dimension in models
    embedding_batch_size: int = 32

    # OpenAI Configuration
    openai_api_key: str | None = None
    openai_base_url: str | None = None  # Custom base URL for OpenAI-compatible APIs
    openai_embedding_model: str = "text-embedding-3-small"

    # Cohere Configuration
    cohere_api_key: str | None = None
    cohere_embedding_model: str = "embed-english-v3.0"

    # SentenceTransformers Configuration
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    sentence_transformer_device: str = "cpu"  # cpu, cuda

    # File Processing Limits
    max_file_size_mb: int = 50  # Maximum file size to process
    timeout_seconds: int = 300  # Processing timeout

    # Retry Configuration
    max_retries: int = 3
    retry_delay_seconds: int = 2

    def get_api_key(self, service: str) -> str | None:
        """Get API key for specified service."""
        if service == "openai":
            return (
                self.openai_api_key
                or llm_config.api_key
                or os.getenv("OPENAI_API_KEY")
            )
        if service == "cohere":
            return (
                self.cohere_api_key
                or llm_config.cohere_api_key
                or os.getenv("COHERE_API_KEY")
            )
        if service == "unstructured":
            return self.unstructured_api_key or os.getenv("UNSTRUCTURED_API_KEY")
        if service == "llamacloud":
            return self.llama_cloud_api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        return None

    def get_embedding_model(self) -> str:
        """Get embedding model with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_EMBEDDING_MODEL"):
            return self.embedding_model
        return llm_config.embedding_model

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_EMBEDDING_DIMENSION"):
            return self.embedding_dimension
        return llm_config.embedding_dimension

    def get_embedding_batch_size(self) -> int:
        """Get embedding batch size with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_EMBEDDING_BATCH_SIZE"):
            return self.embedding_batch_size
        return llm_config.embedding_batch_size

    def get_openai_base_url(self) -> str | None:
        """Get OpenAI base URL with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_OPENAI_BASE_URL"):
            return self.openai_base_url
        return llm_config.base_url

    def get_openai_embedding_model(self) -> str:
        """Get OpenAI embedding model with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_OPENAI_EMBEDDING_MODEL"):
            return self.openai_embedding_model
        return llm_config.openai_embedding_model

    def get_cohere_embedding_model(self) -> str:
        """Get Cohere embedding model with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_COHERE_EMBEDDING_MODEL"):
            return self.cohere_embedding_model
        return llm_config.cohere_embedding_model

    def get_sentence_transformer_model(self) -> str:
        """Get SentenceTransformers model with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_SENTENCE_TRANSFORMER_MODEL"):
            return self.sentence_transformer_model
        return llm_config.sentence_transformer_model

    def get_sentence_transformer_device(self) -> str:
        """Get SentenceTransformers device with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_ETL_SENTENCE_TRANSFORMER_DEVICE"):
            return self.sentence_transformer_device
        return llm_config.sentence_transformer_device

    def validate_service_config(self, service: str) -> bool:
        """Validate that service has required configuration."""
        if service == "unstructured":
            return self.unstructured_api_key is not None
        if service == "llamacloud":
            return self.llama_cloud_api_key is not None
        if service == "docling":
            return self.docling_enabled
        if service == "openai":
            return self.openai_api_key is not None
        if service == "cohere":
            return self.cohere_api_key is not None
        return True


# Global config instance
etl_config = ETLConfig()
