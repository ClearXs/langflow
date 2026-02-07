import pytest

from langflow.services.vector.entity_vector_store import EntityVectorMetadata, EntityVectorStore


class FakeVectorStore:
    def __init__(self):
        self.created_collections = []
        self.added = []
        self.search_calls = []
        self.deleted = []

    async def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.created_collections

    async def create_collection(self, collection_name: str, dimension: int, metadata_schema=None) -> None:
        self.created_collections.append(collection_name)

    async def add_vectors(self, collection_name: str, vectors, metadatas):
        self.added.append((collection_name, vectors, metadatas))
        return [str(md.chunk_id) for md in metadatas]

    async def search(self, collection_name: str, query_vector, top_k=10, filter_dict=None):
        self.search_calls.append((collection_name, query_vector, top_k, filter_dict))
        return []

    async def delete_vectors(self, collection_name: str, chunk_ids):
        self.deleted.append((collection_name, chunk_ids))

    async def get_collection_stats(self, collection_name: str):
        return {"vector_count": 0, "dimension": 3}


@pytest.mark.asyncio
async def test_entity_vector_store_add_and_search(monkeypatch):
    fake_store = FakeVectorStore()

    async def _noop():
        return None

    import langflow.services.vector.entity_vector_store as module

    monkeypatch.setattr(module, "get_vector_store", lambda: fake_store)
    monkeypatch.setattr(module, "initialize_vector_store", _noop)

    store = EntityVectorStore()
    await store.ensure_collection(space_id=1, dimension=3)

    metadata = EntityVectorMetadata(
        entity_id=42,
        space_id=1,
        entity_type="Person",
        graph_node_id="node-42",
        document_id=7,
    )
    await store.add_entity_vectors(1, [[0.1, 0.2, 0.3]], [metadata])

    assert fake_store.added
    collection_name, vectors, metadatas = fake_store.added[0]
    assert collection_name == "space_1_entities"
    assert vectors == [[0.1, 0.2, 0.3]]
    assert metadatas[0].chunk_id == 42
    assert metadatas[0].chunk_type == "entity"
    assert metadatas[0].metadata["entity_type"] == "Person"

    await store.search_entity_vectors(1, [0.1, 0.2, 0.3], top_k=5, filter_dict={"entity_type": "Person"})
    assert fake_store.search_calls
