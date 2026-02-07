import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.entity import Entity
from langflow.services.database.models.relation import Relation
from langflow.services.retrieval.hybrid_search import HybridRetrievalService


@pytest.mark.asyncio
async def test_build_graph_paths_filters_relations():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        e1 = Entity(id=1, space_id=1, document_id=None, chunk_id=None, name="A", entity_type="Person")
        e2 = Entity(id=2, space_id=1, document_id=None, chunk_id=None, name="B", entity_type="Org")
        e3 = Entity(id=3, space_id=1, document_id=None, chunk_id=None, name="C", entity_type="Org")
        session.add_all([e1, e2, e3])
        await session.commit()

        r1 = Relation(
            space_id=1,
            source_entity_id=1,
            target_entity_id=2,
            relation_type="RELATED_TO",
            weight=0.7,
        )
        r2 = Relation(
            space_id=1,
            source_entity_id=1,
            target_entity_id=3,
            relation_type="CAUSES",
            weight=0.5,
        )
        session.add_all([r1, r2])
        await session.commit()

        paths = await HybridRetrievalService._build_graph_paths(
            session=session,
            space_id=1,
            entity_ids=[1, 2, 3],
            relation_types=["RELATED_TO"],
            limit=10,
        )

        assert len(paths) == 1
        assert paths[0]["relation_type"] == "RELATED_TO"
