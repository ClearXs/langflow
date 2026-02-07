import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.entity.model import Entity
from langflow.services.database.models.relation.model import Relation
from langflow.services.graph.binding_sync import index_entities_in_vector_store, sync_graph_bindings_from_neo4j
from langflow.services.graph.neo4j_service import GraphEdge, GraphNode, GraphQueryResult


class FakeGraphService:
    async def fetch_document_graph(self, space_id: int, document_id: int, limit: int = 200):
        return GraphQueryResult(
            nodes=[
                GraphNode(
                    id="node-1",
                    name="Alice",
                    entity_type="Person",
                    description="Engineer",
                    aliases=["A"],
                    properties={},
                    space_id=space_id,
                    document_id=document_id,
                    chunk_id=None,
                ),
                GraphNode(
                    id="node-2",
                    name="Acme",
                    entity_type="Organization",
                    description=None,
                    aliases=[],
                    properties={},
                    space_id=space_id,
                    document_id=document_id,
                    chunk_id=None,
                ),
            ],
            edges=[
                GraphEdge(
                    id="edge-1",
                    source="node-1",
                    target="node-2",
                    relation_type="WORKS_FOR",
                    description=None,
                    weight=0.9,
                    properties={},
                )
            ],
            raw_paths=[],
        )


class FakeEmbeddingService:
    dimension = 3

    async def embed_batch(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeEntityVectorStore:
    def __init__(self):
        self.ensure_calls = []
        self.add_calls = []

    async def ensure_collection(self, space_id: int, dimension: int):
        self.ensure_calls.append((space_id, dimension))

    async def add_entity_vectors(self, space_id: int, vectors, metadatas):
        self.add_calls.append((space_id, vectors, metadatas))


@pytest.mark.asyncio
async def test_sync_graph_bindings_creates_entities_and_relations(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    import langflow.services.graph.binding_sync as module

    monkeypatch.setattr(module, "get_neo4j_graph_service", lambda: FakeGraphService())

    async with async_session() as session:
        entities = await sync_graph_bindings_from_neo4j(session, space_id=1, document_id=2)

        assert len(entities) == 2

        entity_rows = (await session.exec(select(Entity))).all()
        relation_rows = (await session.exec(select(Relation))).all()

        assert len(entity_rows) == 2
        assert len(relation_rows) == 1
        assert relation_rows[0].relation_type == "WORKS_FOR"


@pytest.mark.asyncio
async def test_index_entities_in_vector_store(monkeypatch):
    fake_store = FakeEntityVectorStore()

    import langflow.services.graph.binding_sync as module

    monkeypatch.setattr(module, "get_embedding_service", lambda: FakeEmbeddingService())
    monkeypatch.setattr(module, "EntityVectorStore", lambda: fake_store)

    entities = [
        Entity(
            id=10,
            space_id=1,
            document_id=2,
            chunk_id=None,
            name="Alice",
            entity_type="Person",
            description="Engineer",
            aliases=[],
            properties={},
            graph_node_id="node-1",
        )
    ]

    await index_entities_in_vector_store(entities)

    assert fake_store.ensure_calls == [(1, 3)]
    assert fake_store.add_calls
