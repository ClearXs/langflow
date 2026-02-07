"""Graphs API endpoints - For knowledge graph querying and visualization."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.entity import get_entity_by_id
from langflow.services.database.models.role import Permission
from langflow.services.graph.neo4j_service import get_neo4j_graph_service
from langflow.services.graph.schema import GraphQueryResponse
from langflow.utils.rbac import check_permission

router = APIRouter(prefix="/graphs", tags=["graphs"])


class SubgraphRequest(BaseModel):
    """Subgraph query request."""

    entity_ids: list[int]
    max_depth: int = 2
    max_nodes: int = 100


class EntityRelationsResponse(BaseModel):
    """Entity relations response."""

    entity_id: int
    graph: GraphQueryResponse


@router.post("/{space_id}/subgraph", response_model=GraphQueryResponse)
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

        graph_node_ids: list[str] = []
        for entity_id in request.entity_ids:
            entity = await get_entity_by_id(db, entity_id)
            if not entity or entity.space_id != space_id:
                raise HTTPException(status_code=404, detail="Entity not found")
            if entity.graph_node_id:
                graph_node_ids.append(entity.graph_node_id)

        if not graph_node_ids:
            return GraphQueryResponse(nodes=[], edges=[], raw_paths=[])

        graph_service = get_neo4j_graph_service()
        result = await graph_service.fetch_subgraph(
            space_id=space_id,
            graph_node_ids=graph_node_ids,
            depth=request.max_depth,
            limit=request.max_nodes,
            session=db,  # Pass DB session for document title lookup
        )

        return GraphQueryResponse(
            nodes=[node.__dict__ for node in result.nodes],
            edges=[edge.__dict__ for edge in result.edges],
            raw_paths=result.raw_paths,
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

        entity = await get_entity_by_id(db, entity_id)
        if not entity or entity.space_id != space_id:
            raise HTTPException(status_code=404, detail="Entity not found")

        if not entity.graph_node_id:
            raise HTTPException(status_code=404, detail="Entity graph node not found")

        graph_service = get_neo4j_graph_service()
        result = await graph_service.fetch_entity_relations(
            space_id=space_id,
            graph_node_id=entity.graph_node_id,
            direction=direction,
            session=db,  # Pass DB session for document title lookup
        )

        return EntityRelationsResponse(
            entity_id=entity_id,
            graph=GraphQueryResponse(
                nodes=[node.__dict__ for node in result.nodes],
                edges=[edge.__dict__ for edge in result.edges],
                raw_paths=result.raw_paths,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get entity relations: {e!s}"
        ) from e


@router.get("/", response_model=GraphQueryResponse)
async def get_graph(
    space_id: int,
    entity_id: int,
    depth: int = 1,
    limit: int = 200,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get subgraph by single entity ID."""
    try:
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_READ.value,
            "You do not have permission to read graphs in this space",
        )

        entity = await get_entity_by_id(db, entity_id)
        if not entity or entity.space_id != space_id:
            raise HTTPException(status_code=404, detail="Entity not found")

        if not entity.graph_node_id:
            raise HTTPException(status_code=404, detail="Entity graph node not found")

        graph_service = get_neo4j_graph_service()
        result = await graph_service.fetch_subgraph(
            space_id=space_id,
            graph_node_ids=[entity.graph_node_id],
            depth=depth,
            limit=limit,
            session=db,  # Pass DB session for document title lookup
        )

        return GraphQueryResponse(
            nodes=[node.__dict__ for node in result.nodes],
            edges=[edge.__dict__ for edge in result.edges],
            raw_paths=result.raw_paths,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph: {e!s}") from e


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
