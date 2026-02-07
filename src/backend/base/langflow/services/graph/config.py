"""Knowledge Graph Configuration.

Configuration for LightRAG-based knowledge graph extraction:
- Neo4j graph database
- Milvus vector database
- LLM configuration for entity/relation extraction
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from langflow.services.llm.config import llm_config


class KnowledgeGraphConfig(BaseSettings):
    """Configuration for knowledge graph extraction and storage."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LANGFLOW_KG_",
        extra="ignore"
    )

    # Enable/Disable Knowledge Graph
    enabled: bool = True

    # LightRAG Working Directory
    working_dir: str = "./data/lightrag"

    # LLM Configuration for Entity Extraction
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_max_async: int = 4

    # Embedding Configuration (for entity embeddings)
    embedding_model: str = "openai"  # openai, cohere
    embedding_api_key: str | None = None
    embedding_dimension: int = 1536
    embedding_batch_num: int = 32

    # Neo4j Configuration
    neo4j_enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str | None = None
    neo4j_database: str = "neo4j"

    # Milvus Configuration
    milvus_enabled: bool = True
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_user: str = ""
    milvus_password: str = ""

    # Extraction Configuration
    extract_entities: bool = True
    extract_relations: bool = True
    max_entities_per_document: int = 100
    max_relations_per_document: int = 100

    # Query Configuration
    default_query_mode: str = "hybrid"  # naive, local, global, hybrid
    default_top_k: int = 10
    graph_relation_types: str | None = None  # CSV allowlist, e.g. "RELATED_TO,PART_OF"
    graph_recall_limit: int = 50  # Max graph chunks to recall before RRF
    graph_rrf_weight: float = 1.0  # Weight for graph results in RRF fusion

    def get_neo4j_config(self) -> dict:
        """Get Neo4j configuration dictionary."""
        return {
            "uri": self.neo4j_uri,
            "username": self.neo4j_username,
            "password": self.neo4j_password or os.getenv("NEO4J_PASSWORD", ""),
            "database": self.neo4j_database
        }

    def get_milvus_config(self) -> dict:
        """Get Milvus configuration dictionary."""
        return {
            "host": self.milvus_host,
            "port": self.milvus_port,
            "user": self.milvus_user,
            "password": self.milvus_password
        }

    def get_llm_api_key(self) -> str:
        """Get LLM API key with fallback to environment variable."""
        return (
            self.llm_api_key
            or llm_config.api_key
            or os.getenv("OPENAI_API_KEY", "")
        )

    def get_llm_model(self) -> str:
        """Get LLM model with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_KG_LLM_MODEL"):
            return self.llm_model
        return llm_config.llm_model

    def get_llm_base_url(self) -> str | None:
        """Get LLM base URL with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_KG_LLM_BASE_URL"):
            return self.llm_base_url
        return llm_config.base_url

    def get_llm_max_async(self) -> int:
        """Get LLM max async with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_KG_LLM_MAX_ASYNC"):
            return self.llm_max_async
        return llm_config.llm_max_async

    def get_embedding_model(self) -> str:
        """Get embedding model with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_KG_EMBEDDING_MODEL"):
            return self.embedding_model
        return llm_config.embedding_model

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_KG_EMBEDDING_DIMENSION"):
            return self.embedding_dimension
        return llm_config.embedding_dimension

    def get_embedding_batch_num(self) -> int:
        """Get embedding batch num with LANGFLOW_LLM_ fallback."""
        if os.getenv("LANGFLOW_KG_EMBEDDING_BATCH_NUM"):
            return self.embedding_batch_num
        return llm_config.embedding_batch_size

    def get_embedding_api_key(self) -> str:
        """Get embedding API key with fallback to environment variable."""
        if self.embedding_api_key:
            return self.embedding_api_key

        embedding_model = self.get_embedding_model()
        if embedding_model == "openai":
            return llm_config.api_key or os.getenv("OPENAI_API_KEY", "")
        if embedding_model == "cohere":
            return llm_config.cohere_api_key or os.getenv("COHERE_API_KEY", "")

        return ""

    def is_available(self) -> bool:
        """Check if knowledge graph is properly configured and available."""
        if not self.enabled:
            return False

        # Check LLM API key
        if not self.get_llm_api_key():
            return False

        # Check Neo4j configuration
        if self.neo4j_enabled and not self.neo4j_password and not os.getenv("NEO4J_PASSWORD"):
            return False

        return True


# Global config instance
kg_config = KnowledgeGraphConfig()
