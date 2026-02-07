"""ChromaDB vector storage implementation."""

import logging
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from langflow.services.vector.base import BaseVectorStore, VectorMetadata, VectorSearchResult

logger = logging.getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB implementation of vector storage."""

    def __init__(
        self, persist_directory: str = "./chroma_db", host: str | None = None, port: int | None = None
    ):
        """Initialize ChromaDB client.

        Args:
            persist_directory: Directory for local persistence (local mode)
            host: ChromaDB server host (client mode)
            port: ChromaDB server port (client mode)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB is not installed. Install with: pip install chromadb"
            )

        self.persist_directory = persist_directory
        self.host = host
        self.port = port
        self.client = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize ChromaDB connection."""
        if self._initialized:
            logger.debug("ChromaDB already initialized")
            return

        try:
            if self.host and self.port:
                # Client mode (remote ChromaDB server)
                self.client = chromadb.HttpClient(host=self.host, port=self.port)
                logger.info(f"Connected to ChromaDB server at {self.host}:{self.port}")
            else:
                # Local mode (embedded ChromaDB)
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )
                logger.info(f"Initialized local ChromaDB at {self.persist_directory}")

            # Test connection
            self.client.heartbeat()
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise ConnectionError(f"ChromaDB initialization failed: {e}") from e

    async def create_collection(
        self, collection_name: str, dimension: int, metadata_schema: dict[str, Any] | None = None
    ) -> None:
        """Create a ChromaDB collection."""
        if not self._initialized:
            await self.initialize()

        try:
            # Check if collection already exists
            existing_collections = self.client.list_collections()
            if any(col.name == collection_name for col in existing_collections):
                logger.info(f"Collection {collection_name} already exists, skipping creation")
                return

            # Create collection
            # ChromaDB infers dimension from first vector
            # Metadata schema is optional (Chroma supports dynamic metadata)
            collection_metadata = {"dimension": dimension}
            if metadata_schema:
                collection_metadata.update(metadata_schema)

            self.client.create_collection(name=collection_name, metadata=collection_metadata)

            logger.info(f"Created ChromaDB collection: {collection_name} (dimension={dimension})")

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise

    async def add_vectors(
        self, collection_name: str, vectors: list[list[float]], metadatas: list[VectorMetadata]
    ) -> list[str]:
        """Add vectors to ChromaDB collection."""
        if not self._initialized:
            await self.initialize()

        if len(vectors) != len(metadatas):
            raise ValueError(
                f"Vectors and metadatas length mismatch: {len(vectors)} vs {len(metadatas)}"
            )

        try:
            collection = self.client.get_collection(name=collection_name)

            # ChromaDB requires IDs as strings
            ids = [str(meta.chunk_id) for meta in metadatas]

            # Convert VectorMetadata to Chroma metadata format
            chroma_metadatas = [meta.to_dict() for meta in metadatas]

            # Add to Chroma (upsert behavior - will update if ID exists)
            collection.upsert(ids=ids, embeddings=vectors, metadatas=chroma_metadatas)

            logger.info(f"Added {len(vectors)} vectors to {collection_name}")
            return ids

        except Exception as e:
            logger.error(f"Failed to add vectors to {collection_name}: {e}")
            raise RuntimeError(f"Failed to add vectors: {e}") from e

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search ChromaDB collection."""
        if not self._initialized:
            await self.initialize()

        try:
            collection = self.client.get_collection(name=collection_name)

            # Convert filter to Chroma where clause
            # Chroma uses simple equality filters: {"field": "value"}
            where_clause = filter_dict if filter_dict else None

            # Search
            results = collection.query(query_embeddings=[query_vector], n_results=top_k, where=where_clause)

            # Parse results
            search_results = []
            if results and results["ids"] and len(results["ids"]) > 0:
                for idx, chunk_id_str in enumerate(results["ids"][0]):
                    chunk_id = int(chunk_id_str)

                    # Get distance (Chroma uses L2 distance by default)
                    distance = results["distances"][0][idx] if results["distances"] else 0.0

                    # Get metadata
                    metadata = results["metadatas"][0][idx] if results["metadatas"] else {}

                    # Convert distance to similarity score
                    # For L2 distance: similarity = 1 / (1 + distance)
                    score = 1.0 / (1.0 + distance)

                    search_results.append(
                        VectorSearchResult(chunk_id=chunk_id, score=score, distance=distance, metadata=metadata)
                    )

            logger.info(f"Found {len(search_results)} results in {collection_name}")
            return search_results

        except Exception as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            raise RuntimeError(f"Search failed: {e}") from e

    async def delete_vectors(self, collection_name: str, chunk_ids: list[int]) -> None:
        """Delete vectors from ChromaDB."""
        if not self._initialized:
            await self.initialize()

        try:
            collection = self.client.get_collection(name=collection_name)

            ids = [str(chunk_id) for chunk_id in chunk_ids]
            collection.delete(ids=ids)

            logger.info(f"Deleted {len(chunk_ids)} vectors from {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete vectors from {collection_name}: {e}")
            raise RuntimeError(f"Delete failed: {e}") from e

    async def delete_collection(self, collection_name: str) -> None:
        """Delete ChromaDB collection."""
        if not self._initialized:
            await self.initialize()

        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise ValueError(f"Collection deletion failed: {e}") from e

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get ChromaDB collection statistics."""
        if not self._initialized:
            await self.initialize()

        try:
            collection = self.client.get_collection(name=collection_name)

            count = collection.count()
            metadata = collection.metadata

            return {"vector_count": count, "dimension": metadata.get("dimension"), "metadata": metadata}

        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            raise ValueError(f"Collection not found: {collection_name}") from e

    async def list_collections(self) -> list[str]:
        """List all collections in ChromaDB.

        Returns:
            List of collection names
        """
        if not self._initialized:
            await self.initialize()

        try:
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]
            logger.debug(f"Found {len(collection_names)} collections")
            return collection_names

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise RuntimeError(f"Failed to list collections: {e}") from e

    async def reset(self) -> None:
        """Reset ChromaDB (delete all collections) - for testing only."""
        if not self._initialized:
            await self.initialize()

        logger.warning("Resetting ChromaDB - all collections will be deleted!")
        self.client.reset()
