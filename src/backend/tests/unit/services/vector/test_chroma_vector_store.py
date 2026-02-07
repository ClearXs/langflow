import random

import pytest

from langflow.services.vector.base import VectorMetadata
from langflow.services.vector.chroma_store import CHROMADB_AVAILABLE, ChromaVectorStore


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
async def test_chroma_vector_store_workflow(tmp_path):
    store = ChromaVectorStore(persist_directory=str(tmp_path))
    await store.initialize()

    collection_name = "test_space_1_chunks"
    dimension = 8

    await store.create_collection(collection_name=collection_name, dimension=dimension)

    vectors = [[random.random() for _ in range(dimension)] for _ in range(5)]
    metadatas = [
        VectorMetadata(
            chunk_id=i + 1,
            document_id=1,
            space_id=1,
            chunk_index=i,
            chunk_type="text",
            metadata={"document_id": 1, "test": True},
        )
        for i in range(5)
    ]
    ids = await store.add_vectors(collection_name=collection_name, vectors=vectors, metadatas=metadatas)
    assert len(ids) == 5

    stats = await store.get_collection_stats(collection_name)
    assert stats["vector_count"] == 5
    assert stats["dimension"] == dimension

    results = await store.search(collection_name, query_vector=vectors[0], top_k=3)
    assert len(results) == 3

    filtered = await store.search(
        collection_name,
        query_vector=vectors[0],
        top_k=3,
        filter_dict={"document_id": 1},
    )
    assert len(filtered) == 3

    collections = await store.list_collections()
    assert collection_name in collections

    await store.delete_vectors(collection_name, chunk_ids=[1, 2])
    stats_after = await store.get_collection_stats(collection_name)
    assert stats_after["vector_count"] == 3

    await store.delete_collection(collection_name)
