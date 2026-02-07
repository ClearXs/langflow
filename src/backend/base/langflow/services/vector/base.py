"""Base interface for vector storage engines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class VectorEngineType(str, Enum):
    """Supported vector storage engines."""

    CHROMA = "chroma"
    MILVUS = "milvus"
    SQLITE_VEC = "sqlite_vec"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    PGVECTOR = "pgvector"  # Keep for backward compatibility


@dataclass
class VectorMetadata:
    """Metadata for vector storage."""

    chunk_id: int
    document_id: int
    space_id: int
    chunk_index: int
    chunk_type: str = "text"
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        result = {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "space_id": self.space_id,
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
        }
        if self.metadata:
            result.update(self.metadata)
        return result


@dataclass
class VectorSearchResult:
    """Vector search result."""

    chunk_id: int
    score: float
    distance: float | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}


class BaseVectorStore(ABC):
    """Abstract base class for vector storage engines."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector store connection.

        This method should:
        - Establish connection to the vector database
        - Validate configuration
        - Prepare for operations

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def create_collection(
        self, collection_name: str, dimension: int, metadata_schema: dict[str, Any] | None = None
    ) -> None:
        """Create a vector collection/index.

        Args:
            collection_name: Name of the collection (e.g., "space_1_chunks")
            dimension: Vector dimension (e.g., 3072)
            metadata_schema: Optional metadata schema for filtering

        Raises:
            ValueError: If collection already exists or invalid parameters
        """
        pass

    @abstractmethod
    async def add_vectors(
        self, collection_name: str, vectors: list[list[float]], metadatas: list[VectorMetadata]
    ) -> list[str]:
        """Add vectors to the collection.

        Args:
            collection_name: Collection name
            vectors: List of embedding vectors (each with same dimension)
            metadatas: List of metadata for each vector

        Returns:
            List of vector IDs (usually chunk_id as string)

        Raises:
            ValueError: If vectors and metadatas length mismatch
            RuntimeError: If operation fails
        """
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors.

        Args:
            collection_name: Collection name
            query_vector: Query embedding
            top_k: Number of results to return
            filter_dict: Optional metadata filters (e.g., {"document_id": 123})

        Returns:
            List of search results with chunk_id and similarity score

        Raises:
            ValueError: If collection doesn't exist
            RuntimeError: If search fails
        """
        pass

    @abstractmethod
    async def delete_vectors(self, collection_name: str, chunk_ids: list[int]) -> None:
        """Delete vectors by chunk IDs.

        Args:
            collection_name: Collection name
            chunk_ids: List of chunk IDs to delete

        Raises:
            ValueError: If collection doesn't exist
            RuntimeError: If deletion fails
        """
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None:
        """Delete a collection.

        Args:
            collection_name: Collection name to delete

        Raises:
            ValueError: If collection doesn't exist
        """
        pass

    @abstractmethod
    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics.

        Args:
            collection_name: Collection name

        Returns:
            Dictionary with stats:
            - vector_count: Number of vectors in collection
            - dimension: Vector dimension
            - Additional engine-specific stats

        Raises:
            ValueError: If collection doesn't exist
        """
        pass

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists.

        Args:
            collection_name: Collection name

        Returns:
            True if collection exists, False otherwise
        """
        try:
            await self.get_collection_stats(collection_name)
            return True
        except (ValueError, Exception):
            return False
