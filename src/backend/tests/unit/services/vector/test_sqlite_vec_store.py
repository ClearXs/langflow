import pytest

from langflow.services.vector.base import VectorEngineType, VectorMetadata
from langflow.services.vector.config import VectorStoreConfig
from langflow.services.vector.factory import create_vector_store
from langflow.services.vector.sqlite_vec_store import SqliteVecStore


pytestmark = pytest.mark.asyncio


async def test_sqlite_vec_store_structure():
    required = {
        "initialize",
        "collection_exists",
        "create_collection",
        "add_vectors",
        "search",
        "delete_vectors",
        "delete_collection",
        "get_collection_stats",
        "list_collections",
        "reset",
        "close",
    }
    for method in required:
        assert hasattr(SqliteVecStore, method)


async def test_sqlite_vec_store_workflow(tmp_path):
    db_path = tmp_path / "vectors.db"
    store = SqliteVecStore(database_path=str(db_path))

    await store.initialize()
    collection_name = "test_collection"
    dimension = 8
    await store.create_collection(collection_name, dimension)

    exists = await store.collection_exists(collection_name)
    assert exists is True

    vectors = [[float(i) / 10] * dimension for i in range(5)]
    metadatas = [
        VectorMetadata(chunk_id=i + 1, document_id=1, space_id=1, chunk_index=i, chunk_type="text")
        for i in range(5)
    ]
    ids = await store.add_vectors(collection_name, vectors, metadatas)
    assert len(ids) == 5

    stats = await store.get_collection_stats(collection_name)
    assert stats["vector_count"] == 5
    assert stats["dimension"] == dimension

    query_vector = [0.0] * dimension
    results = await store.search(collection_name, query_vector, top_k=3)
    assert len(results) == 3

    filtered = await store.search(collection_name, query_vector, top_k=3, filter_dict={"space_id": 1})
    assert len(filtered) == 3

    collections = await store.list_collections()
    assert collection_name in collections

    await store.delete_vectors(collection_name, [1, 2])
    stats_after = await store.get_collection_stats(collection_name)
    assert stats_after["vector_count"] == 3

    await store.delete_collection(collection_name)
    exists_after = await store.collection_exists(collection_name)
    assert exists_after is False

    await store.close()


async def test_sqlite_vec_cosine_similarity():
    store = SqliteVecStore(database_path=":memory:")
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]

    similarity_same = store._cosine_similarity(vec1, vec2)
    similarity_orthogonal = store._cosine_similarity(vec1, vec3)

    assert abs(similarity_same - 1.0) < 0.0001
    assert abs(similarity_orthogonal - 0.0) < 0.0001


async def test_sqlite_vec_factory_support(tmp_path):
    db_path = tmp_path / "factory.db"
    store = create_vector_store(VectorEngineType.SQLITE_VEC, database_path=str(db_path))
    assert isinstance(store, SqliteVecStore)


async def test_sqlite_vec_config_support():
    config = VectorStoreConfig()
    assert hasattr(config, "sqlite_vec_database_path")
