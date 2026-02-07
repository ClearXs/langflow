"""Vector store factory for creating engine instances."""

import logging

from langflow.services.vector.base import BaseVectorStore, VectorEngineType

logger = logging.getLogger(__name__)


def create_vector_store(engine_type: str | VectorEngineType, **kwargs) -> BaseVectorStore:
    """Factory function to create vector store instance.

    Args:
        engine_type: Type of vector engine (chroma, milvus, sqlite_vec, etc.)
        **kwargs: Engine-specific configuration

    Returns:
        BaseVectorStore instance

    Example:
        # Chroma (local)
        store = create_vector_store(
            VectorEngineType.CHROMA,
            persist_directory="./chroma_db"
        )

        # Milvus
        store = create_vector_store(
            VectorEngineType.MILVUS,
            host="localhost",
            port=19530
        )

        # sqlite-vec
        store = create_vector_store(
            VectorEngineType.SQLITE_VEC,
            database_path="./vectors.db"
        )
    """
    if isinstance(engine_type, str):
        engine_type = VectorEngineType(engine_type.lower())

    if engine_type == VectorEngineType.CHROMA:
        from langflow.services.vector.chroma_store import ChromaVectorStore

        return ChromaVectorStore(**kwargs)

    elif engine_type == VectorEngineType.MILVUS:
        from langflow.services.vector.milvus_store import MilvusVectorStore

        return MilvusVectorStore(**kwargs)

    elif engine_type == VectorEngineType.SQLITE_VEC:
        from langflow.services.vector.sqlite_vec_store import SqliteVecStore

        return SqliteVecStore(**kwargs)

    elif engine_type == VectorEngineType.QDRANT:
        from langflow.services.vector.qdrant_store import QdrantVectorStore

        return QdrantVectorStore(**kwargs)

    elif engine_type == VectorEngineType.WEAVIATE:
        from langflow.services.vector.weaviate_store import WeaviateVectorStore

        return WeaviateVectorStore(**kwargs)

    elif engine_type == VectorEngineType.PGVECTOR:
        # Keep PGVector support for backward compatibility
        from langflow.services.vector.pgvector_store import PGVectorStore

        return PGVectorStore(**kwargs)

    else:
        raise ValueError(f"Unsupported vector engine: {engine_type}")


# Global vector store instance
_vector_store: BaseVectorStore | None = None


def get_vector_store() -> BaseVectorStore:
    """Get global vector store instance.

    Returns:
        BaseVectorStore instance configured from environment variables

    Example:
        store = get_vector_store()
        await store.initialize()
        await store.add_vectors(...)
    """
    global _vector_store

    if _vector_store is None:
        # Load from configuration
        from langflow.services.vector.config import vector_config

        logger.info(f"Creating vector store: {vector_config.engine_type}")

        _vector_store = create_vector_store(
            engine_type=vector_config.engine_type, **vector_config.get_engine_kwargs()
        )

    return _vector_store


async def initialize_vector_store() -> None:
    """Initialize global vector store.

    This should be called during application startup.

    Example:
        # In main.py or startup hook
        await initialize_vector_store()
    """
    store = get_vector_store()
    await store.initialize()
    logger.info(f"Vector store initialized: {type(store).__name__}")


def reset_vector_store() -> None:
    """Reset global vector store instance.

    Useful for testing or reconfiguration.
    """
    global _vector_store
    _vector_store = None
    logger.info("Vector store instance reset")
