"""LightRAG-based knowledge graph extraction task.

This module provides Celery tasks for extracting knowledge graphs
using LightRAG instead of traditional entity extraction.
"""

import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select

from celery.exceptions import Retry

from langflow.services.database.models import Document, Space
from langflow.services.deps import get_celery_app, get_settings_service
from langflow.services.graph.binding_sync import index_entities_in_vector_store, sync_graph_bindings_from_neo4j
from langflow.services.graph.pipeline_status import apply_graph_status, should_skip_graph_extraction

logger = logging.getLogger(__name__)

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        logger.warning(
            "WindowsProactorEventLoopPolicy not available; async subprocess support may fail."
        )


def get_celery_session_maker():
    """Create async session maker for Celery tasks."""
    settings = get_settings_service().settings
    database_url = settings.database_url
    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
        echo=False,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


celery_app = get_celery_app()
_LITRAG_TASK_LOOP: asyncio.AbstractEventLoop | None = None


def _get_task_loop() -> asyncio.AbstractEventLoop:
    global _LITRAG_TASK_LOOP
    if _LITRAG_TASK_LOOP is None or _LITRAG_TASK_LOOP.is_closed():
        _LITRAG_TASK_LOOP = asyncio.new_event_loop()
    return _LITRAG_TASK_LOOP


async def _extract_lightrag_graph(document_id: int, space_id: int) -> dict:
    """Core async function for LightRAG graph extraction.

    Args:
        document_id: Document ID
        space_id: Space ID

    Returns:
        Dictionary with extraction statistics
    """
    async_session_maker = get_celery_session_maker()

    async with async_session_maker() as session:
        # Get document
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Get space
        stmt_space = select(Space).where(Space.id == space_id)
        result_space = await session.execute(stmt_space)
        space = result_space.scalar_one_or_none()

        if not space:
            raise ValueError(f"Space {space_id} not found")

        # Check if knowledge graph is enabled
        if not space.enable_knowledge_graph:
            logger.info(f"Knowledge graph not enabled for space {space_id}")
            apply_graph_status(document, "skipped", skip_reason="disabled")
            await session.commit()
            logger.info(
                "graph_pipeline_status doc=%s space=%s status=skipped reason=disabled",
                document_id,
                space_id,
            )
            return {"entity_count": 0, "relation_count": 0, "skipped": True, "reason": "disabled"}

        skip, reason, content_hash = should_skip_graph_extraction(document, space_id)
        if skip:
            apply_graph_status(document, "skipped", skip_reason=reason, content_hash=content_hash)
            await session.commit()
            logger.info(
                "graph_pipeline_status doc=%s space=%s status=skipped reason=%s",
                document_id,
                space_id,
                reason,
            )
            return {"entity_count": 0, "relation_count": 0, "skipped": True, "reason": reason}

        # Extract graph using LightRAG
        from langflow.services.graph.service import get_graph_service

        graph_service = get_graph_service()

        logger.info(f"Starting LightRAG graph extraction for document {document_id}")
        apply_graph_status(document, "processing", content_hash=content_hash)
        await session.commit()
        logger.info("graph_pipeline_status doc=%s space=%s status=processing", document_id, space_id)

        try:
            result = await graph_service.extract_graph_from_document(
                document_id=document_id,
                content=document.content or "",
                space_id=space_id,
                title=document.title,
            )
        except Exception as e:
            apply_graph_status(document, "failed", error=str(e), content_hash=content_hash)
            await session.commit()
            logger.warning(
                "graph_pipeline_status doc=%s space=%s status=failed error=%s",
                document_id,
                space_id,
                str(e),
            )
            raise

        if result["success"]:
            # Enrich LightRAG nodes/edges with Langflow-required fields
            from langflow.services.graph.neo4j_service import get_neo4j_graph_service

            neo4j_service = get_neo4j_graph_service()
            try:
                enrichment_result = await neo4j_service.enrich_lightrag_nodes_and_edges(
                    space_id=space_id,
                    document_id=document_id,
                )
                logger.info(
                    f"Enriched LightRAG graph for document {document_id}: "
                    f"{enrichment_result['nodes_enriched']} nodes, "
                    f"{enrichment_result['edges_enriched']} edges"
                )
            except Exception as e:
                logger.warning(f"Graph enrichment failed (non-fatal): {e}")

            updated_entities = await sync_graph_bindings_from_neo4j(session, space_id, document_id)
            await index_entities_in_vector_store(updated_entities)
            # Update document with graph statistics
            document.graph_extracted = True
            document.entity_count = result["entity_count"]
            document.relation_count = result["relation_count"]
            apply_graph_status(document, "completed", content_hash=content_hash)
            await session.commit()
            logger.info(
                "graph_pipeline_status doc=%s space=%s status=completed entities=%s relations=%s",
                document_id,
                space_id,
                result["entity_count"],
                result["relation_count"],
            )

            logger.info(
                f"LightRAG graph extraction completed for document {document_id}: "
                f"{result['entity_count']} entities, {result['relation_count']} relations"
            )
        else:
            logger.error(f"LightRAG graph extraction failed: {result.get('error')}")
            apply_graph_status(document, "failed", error=result.get("error"), content_hash=content_hash)
            await session.commit()
            logger.warning(
                "graph_pipeline_status doc=%s space=%s status=failed error=%s",
                document_id,
                space_id,
                result.get("error"),
            )

        return result


async def _mark_graph_retry(document_id: int, space_id: int, error: Exception) -> None:
    async_session_maker = get_celery_session_maker()
    async with async_session_maker() as session:
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()
        if not document:
            return
        retry_count = int((document.document_metadata or {}).get("graph_retry_count", 0)) + 1
        apply_graph_status(
            document,
            "retrying",
            error=str(error),
            retry_count=retry_count,
        )
        await session.commit()
        logger.warning(
            "graph_pipeline_status doc=%s space=%s status=retrying retry=%s error=%s",
            document_id,
            space_id,
            retry_count,
            str(error),
        )


@celery_app.task(
    name="langflow.tasks.extract_lightrag_graph",
    bind=True,
    autoretry_for=(Retry,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 5},
)
def extract_lightrag_graph_task(self, document_id: int, space_id: int):
    """Celery task to extract knowledge graph using LightRAG.

    Args:
        document_id: Document ID
        space_id: Space ID
    """
    loop = _get_task_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(_extract_lightrag_graph(document_id, space_id))
        return result
    except Exception as e:
        logger.error(f"LightRAG graph extraction task failed: {e}")
        loop.run_until_complete(_mark_graph_retry(document_id, space_id, e))
        raise self.retry(exc=e, countdown=10)
    finally:
        pass
