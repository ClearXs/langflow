"""Relation CRUD operations."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.relation.model import Relation
from langflow.services.database.models.relation.schema import RelationCreate, RelationUpdate


async def create_relation(db: AsyncSession, relation_data: RelationCreate) -> Relation:
    """Create a new relation in the database.

    Args:
        db: Database session
        relation_data: Relation creation data

    Returns:
        Created Relation object

    Raises:
        HTTPException: If creation fails
    """
    relation = Relation(**relation_data.model_dump())

    try:
        db.add(relation)
        await db.commit()
        await db.refresh(relation)
        return relation
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create relation: {e!s}") from e


async def get_relation_by_id(db: AsyncSession, relation_id: int) -> Relation | None:
    """Get a relation by ID.

    Args:
        db: Database session
        relation_id: Relation ID

    Returns:
        Relation object or None if not found
    """
    stmt = select(Relation).where(Relation.id == relation_id)
    return (await db.exec(stmt)).first()


async def get_relations_by_space(
    db: AsyncSession,
    space_id: int,
    relation_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Relation]:
    """Get all relations in a space.

    Args:
        db: Database session
        space_id: Space ID
        relation_type: Optional filter by relation type
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of Relation objects
    """
    stmt = select(Relation).where(Relation.space_id == space_id)

    if relation_type:
        stmt = stmt.where(Relation.relation_type == relation_type)

    stmt = stmt.limit(limit).offset(offset).order_by(Relation.created_at.desc())

    result = await db.exec(stmt)
    return list(result.all())


async def get_relations_by_entity(
    db: AsyncSession,
    entity_id: int,
    direction: str = "both",
) -> list[Relation]:
    """Get all relations connected to an entity.

    Args:
        db: Database session
        entity_id: Entity ID
        direction: Direction filter - "outgoing", "incoming", or "both"

    Returns:
        List of Relation objects

    Raises:
        HTTPException: If invalid direction provided
    """
    if direction == "outgoing":
        stmt = select(Relation).where(Relation.source_entity_id == entity_id)
    elif direction == "incoming":
        stmt = select(Relation).where(Relation.target_entity_id == entity_id)
    elif direction == "both":
        stmt = select(Relation).where(
            (Relation.source_entity_id == entity_id) | (Relation.target_entity_id == entity_id)
        )
    else:
        raise HTTPException(
            status_code=400, detail="Invalid direction. Must be 'outgoing', 'incoming', or 'both'"
        )

    stmt = stmt.order_by(Relation.created_at.desc())
    result = await db.exec(stmt)
    return list(result.all())


async def get_relations_by_document(db: AsyncSession, document_id: int) -> list[Relation]:
    """Get all relations extracted from a document.

    Args:
        db: Database session
        document_id: Document ID

    Returns:
        List of Relation objects
    """
    stmt = select(Relation).where(Relation.document_id == document_id).order_by(Relation.created_at.desc())
    result = await db.exec(stmt)
    return list(result.all())


async def get_relations_between_entities(
    db: AsyncSession,
    entity_id_1: int,
    entity_id_2: int,
) -> list[Relation]:
    """Get all relations between two entities (in both directions).

    Args:
        db: Database session
        entity_id_1: First entity ID
        entity_id_2: Second entity ID

    Returns:
        List of Relation objects
    """
    stmt = select(Relation).where(
        ((Relation.source_entity_id == entity_id_1) & (Relation.target_entity_id == entity_id_2))
        | ((Relation.source_entity_id == entity_id_2) & (Relation.target_entity_id == entity_id_1))
    )

    result = await db.exec(stmt)
    return list(result.all())


async def update_relation(
    db: AsyncSession,
    relation_id: int,
    relation_data: RelationUpdate,
) -> Relation:
    """Update a relation.

    Args:
        db: Database session
        relation_id: Relation ID
        relation_data: Relation update data

    Returns:
        Updated Relation object

    Raises:
        HTTPException: If relation not found or update fails
    """
    relation = await get_relation_by_id(db, relation_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    update_data = relation_data.model_dump(exclude_unset=True)
    changed = False

    for attr, value in update_data.items():
        if hasattr(relation, attr) and value is not None:
            setattr(relation, attr, value)
            flag_modified(relation, attr)
            changed = True

    if not changed:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Nothing to update")

    relation.updated_at = datetime.now(timezone.utc)
    flag_modified(relation, "updated_at")

    try:
        await db.commit()
        await db.refresh(relation)
        return relation
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update relation: {e!s}") from e


async def delete_relation(db: AsyncSession, relation_id: int) -> None:
    """Delete a relation by ID.

    Args:
        db: Database session
        relation_id: Relation ID

    Raises:
        HTTPException: If relation not found
    """
    relation = await get_relation_by_id(db, relation_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    try:
        await db.delete(relation)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete relation: {e!s}") from e


async def delete_relations_by_entity(db: AsyncSession, entity_id: int) -> int:
    """Delete all relations connected to an entity.

    Args:
        db: Database session
        entity_id: Entity ID

    Returns:
        Number of relations deleted
    """
    # Get all relations
    relations = await get_relations_by_entity(db, entity_id, direction="both")

    count = len(relations)
    for relation in relations:
        await db.delete(relation)

    try:
        await db.commit()
        return count
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete relations: {e!s}") from e


async def get_subgraph(
    db: AsyncSession,
    entity_ids: list[int],
    max_depth: int = 2,
    max_nodes: int = 100,
) -> dict:
    """Get a subgraph starting from given entities.

    Args:
        db: Database session
        entity_ids: List of starting entity IDs
        max_depth: Maximum depth to traverse
        max_nodes: Maximum number of nodes to return

    Returns:
        Dictionary with 'entities' and 'relations' lists
    """
    from langflow.services.database.models.entity.model import Entity

    visited_entities = set(entity_ids)
    all_relations = []
    current_entities = set(entity_ids)

    # BFS traversal
    for _ in range(max_depth):
        if len(visited_entities) >= max_nodes:
            break

        next_entities = set()

        for entity_id in current_entities:
            # Get all relations for this entity
            relations = await get_relations_by_entity(db, entity_id, direction="both")
            all_relations.extend(relations)

            # Add connected entities
            for relation in relations:
                if relation.source_entity_id not in visited_entities:
                    next_entities.add(relation.source_entity_id)
                if relation.target_entity_id not in visited_entities:
                    next_entities.add(relation.target_entity_id)

        visited_entities.update(next_entities)
        current_entities = next_entities

        if not current_entities:
            break

    # Get all entities
    stmt = select(Entity).where(Entity.id.in_(list(visited_entities)[:max_nodes]))
    result = await db.exec(stmt)
    entities = list(result.all())

    # Deduplicate relations
    unique_relations = {r.id: r for r in all_relations}.values()

    return {"entities": entities, "relations": list(unique_relations)}
