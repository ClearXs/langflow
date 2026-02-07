"""Synchronize Neo4j graph data to Postgres bindings and vector store."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select

from langflow.services.database.models.entity.model import Entity
from langflow.services.database.models.relation.model import Relation
from langflow.services.etl.embeddings import get_embedding_service
from langflow.services.graph.neo4j_service import get_neo4j_graph_service
from langflow.services.vector.entity_vector_store import EntityVectorMetadata, EntityVectorStore

logger = logging.getLogger(__name__)


async def sync_graph_bindings_from_neo4j(
    session,
    space_id: int,
    document_id: int,
    limit: int = 500,
) -> list[Entity]:
    """Sync Neo4j nodes/edges into Postgres bindings.

    Returns newly created or updated Entity objects.
    """
    graph_service = get_neo4j_graph_service()
    graph = await graph_service.fetch_document_graph(space_id, document_id, limit=limit)
    fallback_to_space = False
    if not graph.nodes:
        graph = await graph_service.fetch_space_graph(space_id, limit=limit)
        fallback_to_space = True

    entities_by_graph_id: dict[str, Entity] = {}
    updated_entities: list[Entity] = []

    for node in graph.nodes:
        stmt = select(Entity).where(Entity.graph_node_id == node.id)
        result = await session.execute(stmt)
        entity = result.scalars().first()

        resolved_document_id = node.document_id
        if resolved_document_id is None and not fallback_to_space:
            resolved_document_id = document_id

        if entity is None:
            entity = Entity(
                space_id=space_id,
                document_id=resolved_document_id,
                chunk_id=node.chunk_id,
                name=node.name or "",
                entity_type=node.entity_type or "Other",
                description=node.description,
                aliases=node.aliases,
                properties=node.properties,
                graph_node_id=node.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(entity)
            updated_entities.append(entity)
        else:
            changed = False
            if entity.document_id is None and resolved_document_id is not None:
                entity.document_id = resolved_document_id
                changed = True
            if node.name and entity.name != node.name:
                entity.name = node.name
                changed = True
            if node.entity_type and entity.entity_type != node.entity_type:
                entity.entity_type = node.entity_type
                changed = True
            if entity.description != node.description:
                entity.description = node.description
                changed = True
            if node.aliases is not None:
                entity.aliases = list(node.aliases)
                flag_modified(entity, "aliases")
                changed = True
            if node.properties is not None:
                entity.properties = dict(node.properties)
                flag_modified(entity, "properties")
                changed = True

            if changed:
                entity.updated_at = datetime.now(timezone.utc)
                flag_modified(entity, "updated_at")
                updated_entities.append(entity)

        entities_by_graph_id[node.id] = entity

    await session.commit()

    for edge in graph.edges:
        if edge.source not in entities_by_graph_id or edge.target not in entities_by_graph_id:
            continue

        stmt = select(Relation).where(Relation.graph_edge_id == edge.id)
        result = await session.execute(stmt)
        relation = result.scalars().first()

        if relation is None:
            relation_document_id = document_id if not fallback_to_space else None
            relation = Relation(
                space_id=space_id,
                source_entity_id=entities_by_graph_id[edge.source].id,
                target_entity_id=entities_by_graph_id[edge.target].id,
                document_id=relation_document_id,
                chunk_id=None,
                relation_type=edge.relation_type,
                description=edge.description,
                weight=edge.weight or 1.0,
                properties=edge.properties,
                graph_edge_id=edge.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(relation)
        else:
            changed = False
            if relation.relation_type != edge.relation_type:
                relation.relation_type = edge.relation_type
                changed = True
            if relation.description != edge.description:
                relation.description = edge.description
                changed = True
            if relation.weight != (edge.weight or relation.weight):
                relation.weight = edge.weight or relation.weight
                changed = True
            if edge.properties is not None:
                relation.properties = dict(edge.properties)
                flag_modified(relation, "properties")
                changed = True
            if changed:
                relation.updated_at = datetime.now(timezone.utc)
                flag_modified(relation, "updated_at")

    await session.commit()

    return updated_entities


async def index_entities_in_vector_store(entities: list[Entity]) -> None:
    """Index entities into the unified vector store."""
    if not entities:
        return

    embedding_service = get_embedding_service()
    store = EntityVectorStore()

    texts = []
    metadatas = []
    space_id = entities[0].space_id

    for entity in entities:
        text = entity.name
        if entity.description:
            text = f"{entity.name}\n{entity.description}"
        texts.append(text)
        metadatas.append(
            EntityVectorMetadata(
                entity_id=entity.id,
                space_id=entity.space_id,
                entity_type=entity.entity_type,
                graph_node_id=entity.graph_node_id,
                document_id=entity.document_id,
            )
        )

    vectors = await embedding_service.embed_batch(texts)
    await store.ensure_collection(space_id=space_id, dimension=embedding_service.dimension)
    await store.add_entity_vectors(space_id=space_id, vectors=vectors, metadatas=metadatas)

    logger.info("Indexed %s entities into vector store", len(entities))
