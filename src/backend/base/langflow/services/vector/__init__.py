"""Vector storage service.

This module provides a unified interface for vector storage across multiple engines:
- ChromaDB (recommended for development)
- Milvus (recommended for production)
- sqlite-vec (lightweight)
- Qdrant (high-performance)
- Weaviate (with knowledge graph)

Usage:
    from langflow.services.vector import get_vector_store, initialize_vector_store
    from langflow.services.vector.base import VectorMetadata

    # Initialize at startup
    await initialize_vector_store()

    # Get instance
    store = get_vector_store()

    # Add vectors
    await store.add_vectors(
        collection_name="space_1_chunks",
        vectors=[[0.1, 0.2, ...], ...],
        metadatas=[VectorMetadata(...), ...]
    )

    # Search
    results = await store.search(
        collection_name="space_1_chunks",
        query_vector=[0.3, 0.4, ...],
        top_k=10
    )
"""

from langflow.services.vector.base import (
    BaseVectorStore,
    VectorEngineType,
    VectorMetadata,
    VectorSearchResult,
)
from langflow.services.vector.config import VectorStoreConfig, vector_config
from langflow.services.vector.factory import (
    create_vector_store,
    get_vector_store,
    initialize_vector_store,
    reset_vector_store,
)

__all__ = [
    # Base classes
    "BaseVectorStore",
    "VectorEngineType",
    "VectorMetadata",
    "VectorSearchResult",
    # Configuration
    "VectorStoreConfig",
    "vector_config",
    # Factory functions
    "create_vector_store",
    "get_vector_store",
    "initialize_vector_store",
    "reset_vector_store",
]
