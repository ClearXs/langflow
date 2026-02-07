import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID

from langflow.services.database.models import Document, Space
from langflow.services.database.models.chunk import Chunk
from langflow.services.database.models.entity import Entity
from langflow.services.database.models.relation import Relation
from langflow.services.retrieval.hybrid_search import HybridRetrievalService
from langflow.services.vector.base import VectorSearchResult


class FakeEmbeddingService:
    async def embed_text(self, text: str):
        return [0.1, 0.2, 0.3]


class FakeEntityVectorStore:
    def __init__(self, entity_ids: list[int]):
        self._entity_ids = entity_ids

    async def search_entity_vectors(self, space_id: int, query_vector, top_k: int = 10, filter_dict=None):
        return [
            VectorSearchResult(
                chunk_id=entity_id,
                score=1.0,
                metadata={"entity_id": entity_id},
            )
            for entity_id in self._entity_ids
        ]


@pytest.mark.asyncio
async def test_graph_search_relation_type_filter_and_recall_limit(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    user_id = UUID("00000000-0000-0000-0000-000000000000")

    async with async_session() as session:
        space = Space(id=1, user_id=user_id, name="space", enable_knowledge_graph=True)
        doc1 = Document(
            id=1,
            space_id=1,
            connector_id=1,
            user_id=user_id,
            title="doc1",
            content="doc1",
            doc_type="FILE",
            unique_identifier_hash="doc1",
        )
        doc2 = Document(
            id=2,
            space_id=1,
            connector_id=1,
            user_id=user_id,
            title="doc2",
            content="doc2",
            doc_type="FILE",
            unique_identifier_hash="doc2",
        )
        doc3 = Document(
            id=3,
            space_id=1,
            connector_id=1,
            user_id=user_id,
            title="doc3",
            content="doc3",
            doc_type="FILE",
            unique_identifier_hash="doc3",
        )
        session.add_all([space, doc1, doc2, doc3])

        chunk1 = Chunk(content="c1", embedding=None, chunk_index=0, token_count=1, chunk_type="text", document_id=1, space_id=1)
        chunk2 = Chunk(content="c2", embedding=None, chunk_index=0, token_count=1, chunk_type="text", document_id=2, space_id=1)
        chunk3 = Chunk(content="c3", embedding=None, chunk_index=0, token_count=1, chunk_type="text", document_id=3, space_id=1)
        session.add_all([chunk1, chunk2, chunk3])

        e1 = Entity(id=1, space_id=1, document_id=1, chunk_id=None, name="E1", entity_type="Person")
        e2 = Entity(id=2, space_id=1, document_id=2, chunk_id=None, name="E2", entity_type="Org")
        e3 = Entity(id=3, space_id=1, document_id=3, chunk_id=None, name="E3", entity_type="Org")
        session.add_all([e1, e2, e3])

        rel_allowed = Relation(
            id=1,
            space_id=1,
            source_entity_id=1,
            target_entity_id=2,
            document_id=1,
            relation_type="RELATED_TO",
            weight=1.0,
        )
        rel_blocked = Relation(
            id=2,
            space_id=1,
            source_entity_id=1,
            target_entity_id=3,
            document_id=1,
            relation_type="CAUSES",
            weight=1.0,
        )
        session.add_all([rel_allowed, rel_blocked])
        await session.commit()

    import langflow.services.etl.embeddings as embeddings_module
    import langflow.services.vector.entity_vector_store as store_module

    monkeypatch.setattr(embeddings_module, "get_embedding_service", lambda: FakeEmbeddingService())
    monkeypatch.setattr(store_module, "EntityVectorStore", lambda: FakeEntityVectorStore([1]))

    async with async_session() as session:
        service = HybridRetrievalService()
        graph_results, document_ids, entity_ids, chunk_ids = await service._graph_search(
            session=session,
            query="test",
            space_id=1,
            top_k=10,
            relation_types=["RELATED_TO"],
            recall_limit=2,
        )

        assert 1 in document_ids
        assert 2 in document_ids
        assert 3 not in document_ids
        assert entity_ids == [1]
        assert chunk_ids

        graph_results_limited, document_ids_limited, _, _ = await service._graph_search(
            session=session,
            query="test",
            space_id=1,
            top_k=10,
            relation_types=["RELATED_TO"],
            recall_limit=1,
        )

        assert len(document_ids_limited) == 1
        assert len(graph_results_limited) == 1
