"""Milvus vector storage implementation."""

import logging
import os
from typing import Any

try:
    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        MilvusClient,
        connections,
        utility,
    )

    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False

from langflow.services.vector.base import BaseVectorStore, VectorMetadata, VectorSearchResult

logger = logging.getLogger(__name__)


class MilvusVectorStore(BaseVectorStore):
    """Milvus implementation of vector storage."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        user: str = "",
        password: str = "",
        db_name: str = "default",
        use_secure: bool = False,
    ):
        """Initialize Milvus client.

        Args:
            host: Milvus server host
            port: Milvus server port
            user: Username for authentication
            password: Password for authentication
            db_name: Database name
            use_secure: Whether to use secure connection (TLS)
        """
        if not MILVUS_AVAILABLE:
            msg = "Milvus is not installed. Install with: pip install pymilvus"
            raise ImportError(msg)

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self.use_secure = use_secure
        self.alias = "default"
        self._initialized = False
        self._collections: dict[str, Collection] = {}

    async def initialize(self) -> None:
        """Initialize Milvus connection."""
        if self._initialized:
            logger.debug("Milvus already initialized")
            return

        try:
            # Connect to Milvus (support Milvus Lite via file path)
            host_value = self.host or ""
            if host_value.startswith("file://"):
                host_value = host_value[7:]

            is_file_uri = (
                bool(host_value)
                and ("/" in host_value or host_value.endswith(".db"))
                and not host_value.startswith(("http://", "https://"))
            )

            if is_file_uri:
                uri = os.path.abspath(os.path.expanduser(host_value))
                connections.connect(
                    alias=self.alias,
                    uri=uri,
                    db_name=self.db_name,
                )
                logger.info(f"Connected to Milvus Lite at {uri}")
            else:
                connections.connect(
                    alias=self.alias,
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    db_name=self.db_name,
                    secure=self.use_secure,
                )
                logger.info(f"Connected to Milvus at {self.host}:{self.port}")

            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Milvus: {e}")
            raise RuntimeError(f"Milvus initialization failed: {e}") from e

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if Milvus collection exists."""
        if not self._initialized:
            await self.initialize()

        try:
            return utility.has_collection(collection_name, using=self.alias)
        except Exception as e:
            logger.error(f"Failed to check collection {collection_name}: {e}")
            return False

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create Milvus collection with schema.

        Schema:
            - id (INT64, primary key, auto-increment)
            - chunk_id (INT64, indexed)
            - embedding (FLOAT_VECTOR, dimension=dimension)
            - document_id (INT64, indexed)
            - space_id (INT64, indexed)
            - chunk_index (INT64)
            - chunk_type (VARCHAR)
        """
        if not self._initialized:
            await self.initialize()

        try:
            if await self.collection_exists(collection_name):
                logger.warning(f"Collection {collection_name} already exists")
                return

            # Define schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="chunk_id", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="document_id", dtype=DataType.INT64),
                FieldSchema(name="space_id", dtype=DataType.INT64),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="chunk_type", dtype=DataType.VARCHAR, max_length=50),
            ]

            schema = CollectionSchema(fields=fields, description=f"Collection for {collection_name}")

            # Create collection
            collection = Collection(name=collection_name, schema=schema, using=self.alias)

            # Create indexes
            # Index on embedding for vector search (IVF_FLAT)
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            }
            collection.create_index(field_name="embedding", index_params=index_params)

            # Load collection into memory
            collection.load()

            self._collections[collection_name] = collection
            logger.info(f"Created collection: {collection_name} with dimension {dimension}")

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise ValueError(f"Collection creation failed: {e}") from e

    async def add_vectors(
        self, collection_name: str, vectors: list[list[float]], metadatas: list[VectorMetadata]
    ) -> list[str]:
        """Add vectors to Milvus collection."""
        if not self._initialized:
            await self.initialize()

        try:
            # Get or create collection
            if collection_name not in self._collections:
                if not await self.collection_exists(collection_name):
                    msg = f"Collection {collection_name} does not exist"
                    raise ValueError(msg)
                self._collections[collection_name] = Collection(name=collection_name, using=self.alias)

            collection = self._collections[collection_name]

            # Prepare data
            entities = [
                [meta.chunk_id for meta in metadatas],  # chunk_id
                vectors,  # embedding
                [meta.document_id for meta in metadatas],  # document_id
                [meta.space_id for meta in metadatas],  # space_id
                [meta.chunk_index for meta in metadatas],  # chunk_index
                [meta.chunk_type for meta in metadatas],  # chunk_type
            ]

            # Insert data
            result = collection.insert(entities)

            # Flush to ensure data is persisted
            collection.flush()

            logger.info(f"Added {len(vectors)} vectors to {collection_name}")
            return [str(pk) for pk in result.primary_keys]

        except Exception as e:
            logger.error(f"Failed to add vectors to {collection_name}: {e}")
            raise RuntimeError(f"Vector insertion failed: {e}") from e

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors in Milvus.

        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional filters (e.g., {"space_id": 1})
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get collection
            if collection_name not in self._collections:
                if not await self.collection_exists(collection_name):
                    logger.warning(f"Collection {collection_name} does not exist")
                    return []
                self._collections[collection_name] = Collection(name=collection_name, using=self.alias)

            collection = self._collections[collection_name]

            # Build filter expression
            expr = None
            if filter_dict:
                conditions = []
                for key, value in filter_dict.items():
                    if isinstance(value, (int, float)):
                        conditions.append(f"{key} == {value}")
                    elif isinstance(value, str):
                        conditions.append(f'{key} == "{value}"')
                if conditions:
                    expr = " && ".join(conditions)

            # Search parameters
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10},
            }

            # Perform search
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["chunk_id", "document_id", "space_id", "chunk_index", "chunk_type"],
            )

            # Parse results
            search_results = []
            for hits in results:
                for hit in hits:
                    # Convert L2 distance to similarity score
                    distance = hit.distance
                    score = 1.0 / (1.0 + distance)

                    metadata = {
                        "document_id": hit.entity.get("document_id"),
                        "space_id": hit.entity.get("space_id"),
                        "chunk_index": hit.entity.get("chunk_index"),
                        "chunk_type": hit.entity.get("chunk_type"),
                    }

                    search_results.append(
                        VectorSearchResult(
                            chunk_id=hit.entity.get("chunk_id"),
                            score=score,
                            distance=distance,
                            metadata=metadata,
                        )
                    )

            logger.info(f"Found {len(search_results)} results in {collection_name}")
            return search_results

        except Exception as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            raise RuntimeError(f"Search failed: {e}") from e

    async def delete_vectors(self, collection_name: str, chunk_ids: list[int]) -> None:
        """Delete vectors from Milvus collection."""
        if not self._initialized:
            await self.initialize()

        try:
            # Get collection
            if collection_name not in self._collections:
                if not await self.collection_exists(collection_name):
                    msg = f"Collection {collection_name} does not exist"
                    raise ValueError(msg)
                self._collections[collection_name] = Collection(name=collection_name, using=self.alias)

            collection = self._collections[collection_name]

            # Build delete expression
            expr = f"chunk_id in {chunk_ids}"
            collection.delete(expr)

            logger.info(f"Deleted {len(chunk_ids)} vectors from {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete vectors from {collection_name}: {e}")
            raise RuntimeError(f"Delete failed: {e}") from e

    async def delete_collection(self, collection_name: str) -> None:
        """Delete Milvus collection."""
        if not self._initialized:
            await self.initialize()

        try:
            if collection_name in self._collections:
                self._collections[collection_name].release()
                del self._collections[collection_name]

            utility.drop_collection(collection_name, using=self.alias)
            logger.info(f"Deleted collection: {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise ValueError(f"Collection deletion failed: {e}") from e

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get Milvus collection statistics."""
        if not self._initialized:
            await self.initialize()

        try:
            # Get collection
            if collection_name not in self._collections:
                if not await self.collection_exists(collection_name):
                    msg = f"Collection {collection_name} does not exist"
                    raise ValueError(msg)
                self._collections[collection_name] = Collection(name=collection_name, using=self.alias)

            collection = self._collections[collection_name]

            # Get stats
            count = collection.num_entities

            # Get schema info
            schema = collection.schema
            dimension = None
            for field in schema.fields:
                if field.name == "embedding":
                    dimension = field.params.get("dim")
                    break

            return {
                "vector_count": count,
                "dimension": dimension,
                "metadata": {"description": schema.description},
            }

        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            raise ValueError(f"Collection not found: {collection_name}") from e

    async def list_collections(self) -> list[str]:
        """List all collections in Milvus.

        Returns:
            List of collection names
        """
        if not self._initialized:
            await self.initialize()

        try:
            collections = utility.list_collections(using=self.alias)
            logger.debug(f"Found {len(collections)} collections")
            return collections

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise RuntimeError(f"Failed to list collections: {e}") from e

    async def reset(self) -> None:
        """Reset Milvus (delete all collections) - for testing only."""
        if not self._initialized:
            await self.initialize()

        try:
            collections = await self.list_collections()
            for collection_name in collections:
                await self.delete_collection(collection_name)

            logger.warning("Milvus reset complete - all collections deleted")

        except Exception as e:
            logger.error(f"Failed to reset Milvus: {e}")
            raise RuntimeError(f"Reset failed: {e}") from e

    async def close(self) -> None:
        """Close Milvus connection."""
        try:
            # Release all loaded collections
            for collection in self._collections.values():
                collection.release()

            self._collections.clear()

            # Disconnect
            connections.disconnect(alias=self.alias)
            self._initialized = False

            logger.info("Milvus connection closed")

        except Exception as e:
            logger.error(f"Failed to close Milvus connection: {e}")
