"""Vector store configuration."""

import os

from pydantic_settings import BaseSettings

from langflow.services.vector.base import VectorEngineType


class VectorStoreConfig(BaseSettings):
    """Configuration for vector storage."""

    # Engine selection
    engine_type: str = "chroma"  # chroma, milvus, sqlite_vec, qdrant, weaviate

    # Chroma configuration
    chroma_persist_directory: str = "./chroma_db"
    chroma_host: str | None = None
    chroma_port: int | None = None

    # Milvus configuration
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_user: str = ""
    milvus_password: str = ""
    milvus_db_name: str = "default"

    # sqlite-vec configuration
    sqlite_vec_database_path: str = "./vectors.db"

    # Qdrant configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None

    # Weaviate configuration
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: str | None = None

    class Config:
        env_file = ".env"
        env_prefix = "LANGFLOW_VECTOR_"
        extra = "ignore"  # Ignore extra fields from .env that don't belong to this config

    def get_engine_kwargs(self) -> dict:
        """Get engine-specific configuration kwargs."""
        engine = VectorEngineType(self.engine_type.lower())

        if engine == VectorEngineType.CHROMA:
            return {
                "persist_directory": self.chroma_persist_directory,
                "host": self.chroma_host,
                "port": self.chroma_port,
            }

        elif engine == VectorEngineType.MILVUS:
            return {
                "host": self.milvus_host,
                "port": self.milvus_port,
                "user": self.milvus_user,
                "password": self.milvus_password,
                "db_name": self.milvus_db_name,
            }

        elif engine == VectorEngineType.SQLITE_VEC:
            return {"database_path": self.sqlite_vec_database_path}

        elif engine == VectorEngineType.QDRANT:
            return {"host": self.qdrant_host, "port": self.qdrant_port, "api_key": self.qdrant_api_key}

        elif engine == VectorEngineType.WEAVIATE:
            return {"url": self.weaviate_url, "api_key": self.weaviate_api_key}

        return {}


# Global configuration instance
vector_config = VectorStoreConfig()
