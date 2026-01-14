"""Graphs API endpoints - For knowledge graph querying and visualization."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.entity import EntityRead
from langflow.services.database.models.relation import (
    Relation,
    RelationRead,
    get_relation_by_id,
    get_relations_by_entity,
    get_subgraph,
)
from langflow.services.database.models.role import Permission
from langflow.utils.rbac import check_permission

router = APIRouter(prefix="/graphs", tags=["graphs"])


class SubgraphRequest(BaseModel):
    """Subgraph query request."""

    entity_ids: list[int]
    max_depth: int = 2
    max_nodes: int = 100


class SubgraphResponse(BaseModel):
    """Subgraph query response."""

    entities: list[EntityRead]
    relations: list[RelationRead]


class EntityRelationsResponse(BaseModel):
    """Entity relations response."""

    entity_id: int
    relations: list[RelationRead]


@router.post("/{space_id}/subgraph", response_model=SubgraphResponse)
async def get_subgraph_endpoint(
    space_id: int,
    request: SubgraphRequest,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get subgraph (for visualization).

    Starting from the given list of entity IDs, perform BFS traversal to get connected entities and relations.

    Args:
        space_id: Space ID
        request: Subgraph request, containing starting entity ID list, maximum depth, and maximum number of nodes

    Requires DOCUMENTS_READ permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_READ.value,
            "You do not have permission to read graphs in this space",
        )

        # Get subgraph
        subgraph_data = await get_subgraph(
            db,
            entity_ids=request.entity_ids,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
        )

        return SubgraphResponse(
            entities=subgraph_data["entities"],
            relations=subgraph_data["relations"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subgraph: {e!s}") from e


@router.get("/{space_id}/entity/{entity_id}/relations", response_model=EntityRelationsResponse)
async def get_entity_relations(
    space_id: int,
    entity_id: int,
    direction: str = "both",  # "outgoing", "incoming", "both"
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get all relations of an entity.

    Args:
        space_id: Space ID
        entity_id: Entity ID
        direction: Relation direction - "outgoing" (outbound edges), "incoming" (inbound edges), or "both" (bidirectional)

    Requires DOCUMENTS_READ permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_READ.value,
            "You do not have permission to read graphs in this space",
        )

        # Get relations
        relations = await get_relations_by_entity(db, entity_id, direction=direction)

        return EntityRelationsResponse(
            entity_id=entity_id,
            relations=relations,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get entity relations: {e!s}"
        ) from e


@router.get("/{space_id}/relation/{relation_id}", response_model=RelationRead)
async def get_relation(
    space_id: int,
    relation_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get relation details.

    Requires DOCUMENTS_READ permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_READ.value,
            "You do not have permission to read graphs in this space",
        )

        relation = await get_relation_by_id(db, relation_id)
        if not relation:
            raise HTTPException(status_code=404, detail="Relation not found")

        # Verify relation belongs to specified space
        if relation.space_id != space_id:
            raise HTTPException(status_code=404, detail="Relation not found")

        return relation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get relation: {e!s}") from e


@router.get("/{space_id}/stats")
async def get_graph_stats(
    space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get graph statistics.

    Returns entity count, relation count, entity type distribution, etc. in the space.

    Requires DOCUMENTS_READ permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_READ.value,
            "You do not have permission to read graphs in this space",
        )

        from sqlalchemy import func
        from sqlmodel import select

        from langflow.services.database.models.entity import Entity
        from langflow.services.database.models.relation import Relation

        # Get total entity count
        stmt_entity_count = select(func.count(Entity.id)).where(Entity.space_id == space_id)
        result_entity_count = await db.execute(stmt_entity_count)
        entity_count = result_entity_count.scalar()

        # Get total relation count
        stmt_relation_count = select(func.count(Relation.id)).where(Relation.space_id == space_id)
        result_relation_count = await db.execute(stmt_relation_count)
        relation_count = result_relation_count.scalar()

        # Get entity type distribution
        stmt_entity_types = (
            select(Entity.entity_type, func.count(Entity.id))
            .where(Entity.space_id == space_id)
            .group_by(Entity.entity_type)
        )
        result_entity_types = await db.execute(stmt_entity_types)
        entity_type_distribution = {row[0]: row[1] for row in result_entity_types.all()}

        # Get relation type distribution
        stmt_relation_types = (
            select(Relation.relation_type, func.count(Relation.id))
            .where(Relation.space_id == space_id)
            .group_by(Relation.relation_type)
        )
        result_relation_types = await db.execute(stmt_relation_types)
        relation_type_distribution = {row[0]: row[1] for row in result_relation_types.all()}

        return {
            "space_id": space_id,
            "entity_count": entity_count,
            "relation_count": relation_count,
            "entity_type_distribution": entity_type_distribution,
            "relation_type_distribution": relation_type_distribution,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get graph statistics: {e!s}"
        ) from e
