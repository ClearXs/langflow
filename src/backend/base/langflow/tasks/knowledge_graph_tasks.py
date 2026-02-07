"""Celery tasks for knowledge graph construction (entity and relation extraction)."""

import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import select

from langflow.services.database.models import Chunk, Document, Entity, Space
from langflow.services.database.models.entity.crud import create_entity
from langflow.services.database.models.relation.crud import create_relation
from langflow.services.deps import get_celery_app, get_settings_service
from langflow.services.graph.config import kg_config
from langflow.services.graph.neo4j_service import get_neo4j_graph_service
from langflow.services.graph.binding_sync import index_entities_in_vector_store
from langflow.services.graph.pipeline_status import apply_graph_status, should_skip_graph_extraction
from langflow.services.knowledge.entity_extraction import EntityExtractionService
from langflow.services.llm.service import LLMService

logger = logging.getLogger(__name__)

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        logger.warning("WindowsProactorEventLoopPolicy not available; async subprocess support may fail.")


def get_celery_session_maker():
    """Create a new async session maker for Celery tasks.

    This is necessary because Celery tasks run in a new event loop,
    and the default session maker is bound to the main app's event loop.
    """
    settings = get_settings_service().settings
    database_url = settings.database_url
    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,  # Don't use connection pooling for Celery tasks
        echo=False,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


celery_app = get_celery_app()


async def _extract_entities_and_relations(
    document_id: int,
    space_id: int,
) -> dict:
    """Core async function for extracting entities and relations from a document.

    Args:
        document_id: Document ID
        space_id: Space ID

    Returns:
        Dictionary containing extraction statistics
    """
    async_session_maker = get_celery_session_maker()

    async with async_session_maker() as session:
        # 1. Get document and space configuration
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        stmt_space = select(Space).where(Space.id == space_id)
        result_space = await session.execute(stmt_space)
        space = result_space.scalar_one_or_none()

        if not space:
            raise ValueError(f"Space {space_id} not found")

        # Check if knowledge graph is enabled
        if not space.enable_knowledge_graph:
            logger.info(f"Knowledge graph not enabled for space {space_id}, skipping entity extraction")
            apply_graph_status(document, "skipped", skip_reason="disabled")
            await session.commit()
            logger.info(
                "graph_pipeline_status doc=%s space=%s status=skipped reason=disabled",
                document_id,
                space_id,
            )
            return {"entities_count": 0, "relations_count": 0, "skipped": True, "reason": "disabled"}

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
            return {"entities_count": 0, "relations_count": 0, "skipped": True, "reason": reason}

        # 2. Get LLM instance
        settings_service = get_settings_service()
        llm_service = LLMService(settings_service)

        # Use graph_llm_id if configured, otherwise use document_summary_llm_id
        llm_config_id = space.graph_llm_id or space.document_summary_llm_id
        if not llm_config_id:
            logger.error(f"No LLM configured for space {space_id}, cannot extract entities")
            raise ValueError("No LLM configured for entity extraction")

        llm = await llm_service.get_llm_by_id(session, llm_config_id)
        if not llm:
            raise ValueError(f"LLM config {llm_config_id} not found")

        apply_graph_status(document, "processing", content_hash=content_hash)
        await session.commit()
        logger.info("graph_pipeline_status doc=%s space=%s status=processing", document_id, space_id)

        try:
            # 3. Get all chunks from the document
            stmt_chunks = select(Chunk).where(Chunk.document_id == document_id)
            result_chunks = await session.execute(stmt_chunks)
            chunks = result_chunks.scalars().all()

            if not chunks:
                logger.warning(f"Document {document_id} has no chunks, trying to use entire document content")
                # Use entire document content
                text_content = document.content or ""
                chunk_id = None
            else:
                # Merge all chunk contents
                text_content = "\n\n".join([chunk.content for chunk in chunks if chunk.content])
                chunk_id = chunks[0].id if chunks else None

            if not text_content:
                logger.warning(f"Document {document_id} has no available content")
                apply_graph_status(document, "skipped", skip_reason="no_content", content_hash=content_hash)
                await session.commit()
                logger.info(
                    "graph_pipeline_status doc=%s space=%s status=skipped reason=no_content",
                    document_id,
                    space_id,
                )
                return {"entities_count": 0, "relations_count": 0, "no_content": True, "skipped": True}

            # 4. Extract entities
            logger.info(f"Starting entity extraction from document {document_id}...")
            entity_creates = await EntityExtractionService.extract_entities_from_text(
                text=text_content,
                llm=llm,
                space_id=space_id,
                document_id=document_id,
                chunk_id=chunk_id,
                max_entities=30,  # Maximum 30 entities per document
            )

            if not entity_creates:
                logger.info(f"No entities extracted from document {document_id}")
                return {"entities_count": 0, "relations_count": 0}

            # 5. Deduplicate entities
            entity_creates = EntityExtractionService.merge_similar_entities(entity_creates)

            # 6. Save entities to database
            created_entities = []
            entities_for_indexing = []
            entity_name_to_id = {}

            graph_service = get_neo4j_graph_service()

            for entity_create in entity_creates:
                try:
                    # Check if entity already exists (based on name and space)
                    stmt_existing = (
                        select(Entity)
                        .where(Entity.space_id == space_id)
                        .where(Entity.name == entity_create.name)
                    )
                    result_existing = await session.execute(stmt_existing)
                    existing_entity = result_existing.scalar_one_or_none()

                    if existing_entity:
                        # Entity already exists, skip creation
                        logger.info(f"Entity '{entity_create.name}' already exists, skipping creation")
                        created_entities.append(existing_entity)
                        entities_for_indexing.append(existing_entity)
                        entity_name_to_id[existing_entity.name] = existing_entity.id
                        if kg_config.neo4j_enabled and not existing_entity.graph_node_id:
                            graph_node_id = await graph_service.upsert_entity(
                                space_id,
                                existing_entity.model_dump(),
                            )
                            if graph_node_id:
                                existing_entity.graph_node_id = graph_node_id
                                await session.commit()
                    else:
                        # Create new entity
                        entity = await create_entity(session, entity_create)
                        if kg_config.neo4j_enabled:
                            graph_node_id = await graph_service.upsert_entity(
                                space_id,
                                entity.model_dump(),
                            )
                            if graph_node_id:
                                entity.graph_node_id = graph_node_id
                                await session.commit()
                        created_entities.append(entity)
                        entities_for_indexing.append(entity)
                        entity_name_to_id[entity.name] = entity.id
                        logger.info(f"Created entity: {entity.name} ({entity.entity_type})")

                except Exception as e:
                    logger.error(f"Failed to create entity: {e}")
                    continue

            # 7. Extract relations
            logger.info(f"Starting relation extraction from document {document_id}...")
            entities_dict = [
                {"name": e.name, "type": e.entity_type} for e in created_entities
            ]

            relations_data = await EntityExtractionService.extract_relations_from_text(
                text=text_content,
                entities=entities_dict,
                llm=llm,
                space_id=space_id,
                document_id=document_id,
                chunk_id=chunk_id,
                max_relations=50,  # Maximum 50 relations per document
            )

            # 8. Save relations to database
            created_relations_count = 0

            for relation_data in relations_data:
                try:
                    source_name = relation_data["source_name"]
                    target_name = relation_data["target_name"]

                    # Find entity IDs
                    source_id = entity_name_to_id.get(source_name)
                    target_id = entity_name_to_id.get(target_name)

                    if not source_id or not target_id:
                        logger.warning(
                            f"Skipping relation {source_name} -> {target_name}: corresponding entities not found"
                        )
                        continue

                    # Ensure graph nodes exist
                    source_entity = await session.get(Entity, source_id)
                    target_entity = await session.get(Entity, target_id)
                    graph_edge_id = None

                    if kg_config.neo4j_enabled and source_entity and target_entity:
                        if not source_entity.graph_node_id:
                            source_entity.graph_node_id = await graph_service.upsert_entity(
                                space_id,
                                source_entity.model_dump(),
                            )
                            await session.commit()
                        if not target_entity.graph_node_id:
                            target_entity.graph_node_id = await graph_service.upsert_entity(
                                space_id,
                                target_entity.model_dump(),
                            )
                            await session.commit()

                        if source_entity.graph_node_id and target_entity.graph_node_id:
                            graph_edge_id = await graph_service.create_relation(
                                space_id=space_id,
                                source_node_id=source_entity.graph_node_id,
                                target_node_id=target_entity.graph_node_id,
                                relation_type=relation_data["relation_type"],
                                description=relation_data.get("description"),
                                weight=relation_data.get("weight", 1.0),
                                properties={},
                            )

                    # Create relation
                    from langflow.services.database.models.relation.schema import RelationCreate

                    relation_create = RelationCreate(
                        space_id=space_id,
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        document_id=document_id,
                        chunk_id=chunk_id,
                        relation_type=relation_data["relation_type"],
                        description=relation_data.get("description"),
                        weight=relation_data.get("weight", 1.0),
                        properties={},
                        graph_edge_id=graph_edge_id,
                    )

                    await create_relation(session, relation_create)
                    created_relations_count += 1
                    logger.info(
                        f"Created relation: {source_name} --[{relation_data['relation_type']}]--> {target_name}"
                    )

                except Exception as e:
                    logger.error(f"Failed to create relation: {e}")
                    continue

            logger.info(
                f"Entity extraction completed for document {document_id}: "
                f"{len(created_entities)} entities, {created_relations_count} relations"
            )

            await index_entities_in_vector_store(entities_for_indexing)

            document.graph_extracted = True
            document.entity_count = len(created_entities)
            document.relation_count = created_relations_count
            apply_graph_status(document, "completed", content_hash=content_hash)
            await session.commit()
            logger.info(
                "graph_pipeline_status doc=%s space=%s status=completed entities=%s relations=%s",
                document_id,
                space_id,
                len(created_entities),
                created_relations_count,
            )

            return {
                "entities_count": len(created_entities),
                "relations_count": created_relations_count,
                "document_id": document_id,
                "space_id": space_id,
            }
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
    name="langflow.tasks.extract_entities_from_document",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 5},
)
def extract_entities_from_document_task(
    self,
    document_id: int,
    space_id: int,
) -> dict:
    """Celery task for extracting entities and relations from a document.

    Args:
        document_id: Document ID
        space_id: Space ID

    Returns:
        Dictionary containing extraction statistics
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _extract_entities_and_relations(document_id, space_id)
        )
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        return result

    except Exception as e:
        logger.error(f"Entity extraction task failed: {e}", exc_info=True)
        loop.run_until_complete(_mark_graph_retry(document_id, space_id, e))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        raise self.retry(exc=e, countdown=10)


@celery_app.task(name="langflow.tasks.extract_entities_from_space", bind=True)
def extract_entities_from_space_task(
    self,
    space_id: int,
    force: bool = False,
) -> dict:
    """Celery task for extracting entities and relations from all documents in a space.

    Args:
        space_id: Space ID
        force: Whether to force re-extraction (even if already extracted)

    Returns:
        Dictionary containing processing statistics
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _process_space():
        async_session_maker = get_celery_session_maker()

        async with async_session_maker() as session:
            # Get all documents in the space
            stmt = select(Document).where(Document.space_id == space_id)
            result = await session.execute(stmt)
            documents = result.scalars().all()

            total_entities = 0
            total_relations = 0
            processed_documents = 0

            for document in documents:
                try:
                    # If not forcing, check if document already has extracted entities
                    if not force:
                        stmt_existing = select(Entity).where(
                            Entity.document_id == document.id
                        )
                        result_existing = await session.execute(stmt_existing)
                        existing_entities = result_existing.scalars().all()

                        if existing_entities:
                            logger.info(f"Document {document.id} already has entities, skipping")
                            continue

                    # Extract entities and relations
                    result = await _extract_entities_and_relations(
                        document.id, space_id
                    )

                    if not result.get("skipped") and not result.get("no_content"):
                        total_entities += result["entities_count"]
                        total_relations += result["relations_count"]
                        processed_documents += 1

                except Exception as e:
                    logger.error(f"Failed to process document {document.id}: {e}")
                    continue

            return {
                "space_id": space_id,
                "processed_documents": processed_documents,
                "total_entities": total_entities,
                "total_relations": total_relations,
            }

    try:
        result = loop.run_until_complete(_process_space())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        return result

    except Exception as e:
        logger.error(f"Space entity extraction task failed: {e}", exc_info=True)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        raise
