"""Entity vector storage adapter.

This adapter maps entity embeddings to the unified vector store interface.
Entities are stored in per-space collections: space_{space_id}_entities
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langflow.services.vector import get_vector_store, initialize_vector_store
from langflow.services.vector.base import VectorMetadata, VectorSearchResult


@dataclass
class EntityVectorMetadata:
    """Metadata for entity vectors."""

    entity_id: int
    space_id: int
    entity_type: str | None = None
    graph_node_id: str | None = None
    document_id: int | None = None

    def to_vector_metadata(self) -> VectorMetadata:
        """Convert to VectorMetadata for storage."""
        return VectorMetadata(
            chunk_id=self.entity_id,
            document_id=self.document_id or 0,
            space_id=self.space_id,
            chunk_index=0,
            chunk_type="entity",
            metadata={
                "entity_id": self.entity_id,
                "entity_type": self.entity_type,
                "graph_node_id": self.graph_node_id,
            },
        )


class EntityVectorStore:
    """Adapter for storing and searching entity embeddings."""

    def __init__(self):
        self._store = get_vector_store()

    @staticmethod
    def collection_name(space_id: int) -> str:
        return f"space_{space_id}_entities"

    async def ensure_collection(self, space_id: int, dimension: int) -> None:
        """Ensure the entity collection exists for a space."""
        await initialize_vector_store()
        collection = self.collection_name(space_id)
        if not await self._store.collection_exists(collection):
            await self._store.create_collection(collection, dimension=dimension)

    async def add_entity_vectors(
        self,
        space_id: int,
        vectors: list[list[float]],
        metadatas: list[EntityVectorMetadata],
    ) -> list[str]:
        """Add entity vectors to the store."""
        await initialize_vector_store()
        collection = self.collection_name(space_id)
        vector_metadatas = [metadata.to_vector_metadata() for metadata in metadatas]
        return await self._store.add_vectors(collection, vectors, vector_metadatas)

    async def search_entity_vectors(
        self,
        space_id: int,
        query_vector: list[float],
        top_k: int = 10,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search entity vectors in the store."""
        await initialize_vector_store()
        collection = self.collection_name(space_id)
        return await self._store.search(collection, query_vector, top_k=top_k, filter_dict=filter_dict)

    async def delete_entity_vectors(self, space_id: int, entity_ids: list[int]) -> None:
        """Delete entity vectors by entity IDs."""
        await initialize_vector_store()
        collection = self.collection_name(space_id)
        await self._store.delete_vectors(collection, entity_ids)

