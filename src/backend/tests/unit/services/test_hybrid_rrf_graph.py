import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.chunk.model import Chunk
from langflow.services.retrieval.hybrid_search import HybridRetrievalService


@pytest.mark.asyncio
async def test_rrf_includes_graph_rank():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        chunk_a = Chunk(
            content="chunk-a",
            embedding=None,
            chunk_index=0,
            token_count=1,
            chunk_type="text",
            document_id=1,
            space_id=1,
        )
        chunk_b = Chunk(
            content="chunk-b",
            embedding=None,
            chunk_index=1,
            token_count=1,
            chunk_type="text",
            document_id=2,
            space_id=1,
        )
        session.add(chunk_a)
        session.add(chunk_b)
        await session.commit()

        service = HybridRetrievalService()
        results = await service._rrf_fusion(
            session=session,
            vector_results=[(chunk_a.id, 0.9)],
            fts_results=[],
            graph_results=[(chunk_b.id, 1.0)],
            top_k=2,
        )

        assert len(results) == 2
        graph_entry = next(item for item in results if item["id"] == chunk_b.id)
        assert graph_entry["graph_rank"] == 1


@pytest.mark.asyncio
async def test_rrf_graph_weight_influences_order():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        chunk_a = Chunk(
            content="chunk-a",
            embedding=None,
            chunk_index=0,
            token_count=1,
            chunk_type="text",
            document_id=1,
            space_id=1,
        )
        chunk_b = Chunk(
            content="chunk-b",
            embedding=None,
            chunk_index=1,
            token_count=1,
            chunk_type="text",
            document_id=2,
            space_id=1,
        )
        session.add(chunk_a)
        session.add(chunk_b)
        await session.commit()

        service = HybridRetrievalService()
        service.graph_weight = 2.0

        results = await service._rrf_fusion(
            session=session,
            vector_results=[(chunk_a.id, 0.9)],
            fts_results=[],
            graph_results=[(chunk_b.id, 1.0)],
            top_k=2,
        )

        assert results[0]["id"] == chunk_b.id
