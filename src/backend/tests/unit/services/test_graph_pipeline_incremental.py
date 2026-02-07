import pytest
from uuid import UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models import Document, Space
from langflow.tasks.knowledge_graph_tasks import _extract_entities_and_relations


@pytest.mark.asyncio
async def test_graph_pipeline_skip_when_no_change(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_maker() as session:
        user_id = UUID("00000000-0000-0000-0000-000000000000")
        space = Space(id=1, user_id=user_id, name="space", enable_knowledge_graph=True)
        doc = Document(
            id=1,
            space_id=1,
            connector_id=1,
            user_id=user_id,
            title="doc",
            content="hello",
            doc_type="FILE",
            unique_identifier_hash="abc",
            content_hash="hash123",
            graph_extracted=True,
            document_metadata={"graph_content_hash": "hash123"},
        )
        session.add(space)
        session.add(doc)
        await session.commit()

    import langflow.tasks.knowledge_graph_tasks as module

    monkeypatch.setattr(module, "get_celery_session_maker", lambda: session_maker)

    result = await _extract_entities_and_relations(document_id=1, space_id=1)
    assert result["skipped"] is True
    assert result["reason"] == "no_change"

    async with session_maker() as session:
        stored = (await session.exec(select(Document).where(Document.id == 1))).one()
        assert stored.document_metadata["graph_status"] == "skipped"
        assert stored.document_metadata["graph_skip_reason"] == "no_change"


@pytest.mark.asyncio
async def test_graph_pipeline_backfill_hash(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_maker() as session:
        user_id = UUID("00000000-0000-0000-0000-000000000000")
        space = Space(id=1, user_id=user_id, name="space", enable_knowledge_graph=True)
        doc = Document(
            id=1,
            space_id=1,
            connector_id=1,
            user_id=user_id,
            title="doc",
            content="hello",
            doc_type="FILE",
            unique_identifier_hash="abc",
            content_hash="hash123",
            graph_extracted=True,
        )
        session.add(space)
        session.add(doc)
        await session.commit()

    import langflow.tasks.knowledge_graph_tasks as module

    monkeypatch.setattr(module, "get_celery_session_maker", lambda: session_maker)

    result = await _extract_entities_and_relations(document_id=1, space_id=1)
    assert result["skipped"] is True
    assert result["reason"] == "backfill_hash"

    async with session_maker() as session:
        stored = (await session.exec(select(Document).where(Document.id == 1))).one()
        assert stored.document_metadata["graph_status"] == "skipped"
        assert stored.document_metadata["graph_skip_reason"] == "backfill_hash"
        assert stored.document_metadata["graph_content_hash"] == "hash123"


@pytest.mark.asyncio
async def test_graph_pipeline_skip_when_disabled(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_maker() as session:
        user_id = UUID("00000000-0000-0000-0000-000000000000")
        space = Space(id=1, user_id=user_id, name="space", enable_knowledge_graph=False)
        doc = Document(
            id=1,
            space_id=1,
            connector_id=1,
            user_id=user_id,
            title="doc",
            content="hello",
            doc_type="FILE",
            unique_identifier_hash="abc",
            content_hash="hash123",
        )
        session.add(space)
        session.add(doc)
        await session.commit()

    import langflow.tasks.knowledge_graph_tasks as module

    monkeypatch.setattr(module, "get_celery_session_maker", lambda: session_maker)

    result = await _extract_entities_and_relations(document_id=1, space_id=1)
    assert result["skipped"] is True
    assert result["reason"] == "disabled"

    async with session_maker() as session:
        stored = (await session.exec(select(Document).where(Document.id == 1))).one()
        assert stored.document_metadata["graph_status"] == "skipped"
        assert stored.document_metadata["graph_skip_reason"] == "disabled"
