import uuid

import pytest

from langflow.services.vector.base import VectorMetadata
from langflow.services.vector.milvus_store import MILVUS_AVAILABLE, MilvusVectorStore


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not MILVUS_AVAILABLE, reason="pymilvus not installed")
async def test_milvus_vector_store_functional_workflow():
    store = MilvusVectorStore(host="localhost", port=19530, db_name="default")
    try:
        await store.initialize()
    except Exception as exc:
        pytest.skip(f"Milvus not available locally: {exc}")

    collection_name = f"test_vectors_{uuid.uuid4().hex[:8]}"
    dimension = 8

    try:
        await store.create_collection(collection_name=collection_name, dimension=dimension)

        collections = await store.list_collections()
        assert collection_name in collections

        vectors = [[float(i) / 10] * dimension for i in range(5)]
        metadatas = [
            VectorMetadata(chunk_id=i + 1, document_id=1, space_id=1, chunk_index=i, chunk_type="text")
            for i in range(5)
        ]
        ids = await store.add_vectors(collection_name=collection_name, vectors=vectors, metadatas=metadatas)
        assert len(ids) == 5

        stats = await store.get_collection_stats(collection_name)
        assert stats["vector_count"] >= 5
        assert stats["dimension"] == dimension

        results = await store.search(collection_name, query_vector=vectors[0], top_k=3)
        assert len(results) == 3

        filtered = await store.search(
            collection_name,
            query_vector=vectors[0],
            top_k=3,
            filter_dict={"space_id": 1},
        )
        assert len(filtered) == 3

        await store.delete_vectors(collection_name, [1, 2])
        stats_after = await store.get_collection_stats(collection_name)
        assert stats_after["vector_count"] <= stats["vector_count"]

    finally:
        await store.delete_collection(collection_name)
        await store.close()
