"""Entity CRUD operations."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.database.models.entity.model import Entity
from langflow.services.database.models.entity.schema import EntityCreate, EntityUpdate


async def create_entity(db: AsyncSession, entity_data: EntityCreate) -> Entity:
    """Create a new entity in the database.

    Args:
        db: Database session
        entity_data: Entity creation data

    Returns:
        Created Entity object

    Raises:
        HTTPException: If creation fails
    """
    entity = Entity(**entity_data.model_dump())

    try:
        db.add(entity)
        await db.commit()
        await db.refresh(entity)
        return entity
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create entity: {e!s}") from e


async def get_entity_by_id(db: AsyncSession, entity_id: int) -> Entity | None:
    """Get an entity by ID.

    Args:
        db: Database session
        entity_id: Entity ID

    Returns:
        Entity object or None if not found
    """
    stmt = select(Entity).where(Entity.id == entity_id)
    return (await db.exec(stmt)).first()


async def get_entities_by_space(
    db: AsyncSession,
    space_id: int,
    entity_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Entity]:
    """Get all entities in a space.

    Args:
        db: Database session
        space_id: Space ID
        entity_type: Optional filter by entity type
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of Entity objects
    """
    stmt = select(Entity).where(Entity.space_id == space_id)

    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)

    stmt = stmt.limit(limit).offset(offset).order_by(Entity.created_at.desc())

    result = await db.exec(stmt)
    return list(result.all())


async def get_entities_by_document(db: AsyncSession, document_id: int) -> list[Entity]:
    """Get all entities extracted from a document.

    Args:
        db: Database session
        document_id: Document ID

    Returns:
        List of Entity objects
    """
    stmt = select(Entity).where(Entity.document_id == document_id).order_by(Entity.created_at.desc())
    result = await db.exec(stmt)
    return list(result.all())


async def get_entities_by_chunk(db: AsyncSession, chunk_id: int) -> list[Entity]:
    """Get all entities extracted from a chunk.

    Args:
        db: Database session
        chunk_id: Chunk ID

    Returns:
        List of Entity objects
    """
    stmt = select(Entity).where(Entity.chunk_id == chunk_id).order_by(Entity.created_at.desc())
    result = await db.exec(stmt)
    return list(result.all())


async def search_entities_by_name(
    db: AsyncSession,
    space_id: int,
    name_query: str,
    limit: int = 50,
) -> list[Entity]:
    """Search entities by name (case-insensitive partial match).

    Args:
        db: Database session
        space_id: Space ID
        name_query: Name search query
        limit: Maximum number of results

    Returns:
        List of Entity objects
    """
    stmt = (
        select(Entity)
        .where(Entity.space_id == space_id)
        .where(Entity.name.ilike(f"%{name_query}%"))
        .limit(limit)
        .order_by(Entity.created_at.desc())
    )

    result = await db.exec(stmt)
    return list(result.all())


async def update_entity(
    db: AsyncSession,
    entity_id: int,
    entity_data: EntityUpdate,
) -> Entity:
    """Update an entity.

    Args:
        db: Database session
        entity_id: Entity ID
        entity_data: Entity update data

    Returns:
        Updated Entity object

    Raises:
        HTTPException: If entity not found or update fails
    """
    entity = await get_entity_by_id(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    update_data = entity_data.model_dump(exclude_unset=True)
    changed = False

    for attr, value in update_data.items():
        if hasattr(entity, attr) and value is not None:
            setattr(entity, attr, value)
            flag_modified(entity, attr)
            changed = True

    if not changed:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Nothing to update")

    entity.updated_at = datetime.now(timezone.utc)
    flag_modified(entity, "updated_at")

    try:
        await db.commit()
        await db.refresh(entity)
        return entity
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update entity: {e!s}") from e


async def delete_entity(db: AsyncSession, entity_id: int) -> None:
    """Delete an entity by ID.

    Args:
        db: Database session
        entity_id: Entity ID

    Raises:
        HTTPException: If entity not found
    """
    entity = await get_entity_by_id(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    try:
        await db.delete(entity)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Cannot delete entity due to existing relations: {e!s}"
        ) from e


async def merge_entities(
    db: AsyncSession,
    source_entity_id: int,
    target_entity_id: int,
) -> Entity:
    """Merge source entity into target entity.

    This combines aliases, properties, and updates relations to point to target entity.

    Args:
        db: Database session
        source_entity_id: Source entity to merge from
        target_entity_id: Target entity to merge into

    Returns:
        Updated target Entity object

    Raises:
        HTTPException: If either entity not found
    """
    source_entity = await get_entity_by_id(db, source_entity_id)
    target_entity = await get_entity_by_id(db, target_entity_id)

    if not source_entity:
        raise HTTPException(status_code=404, detail="Source entity not found")
    if not target_entity:
        raise HTTPException(status_code=404, detail="Target entity not found")

    # Merge aliases (add source name and aliases to target)
    target_aliases = set(target_entity.aliases)
    target_aliases.add(source_entity.name)
    target_aliases.update(source_entity.aliases)
    target_entity.aliases = list(target_aliases)

    # Merge properties (source properties take precedence for conflicts)
    target_entity.properties.update(source_entity.properties)

    flag_modified(target_entity, "aliases")
    flag_modified(target_entity, "properties")
    target_entity.updated_at = datetime.now(timezone.utc)

    # Update all relations pointing to source entity to point to target
    from langflow.services.database.models.relation.model import Relation

    # Update source relations
    stmt_source = select(Relation).where(Relation.source_entity_id == source_entity_id)
    result_source = await db.exec(stmt_source)
    for relation in result_source.all():
        relation.source_entity_id = target_entity_id
        flag_modified(relation, "source_entity_id")

    # Update target relations
    stmt_target = select(Relation).where(Relation.target_entity_id == source_entity_id)
    result_target = await db.exec(stmt_target)
    for relation in result_target.all():
        relation.target_entity_id = target_entity_id
        flag_modified(relation, "target_entity_id")

    try:
        # Delete source entity
        await db.delete(source_entity)
        await db.commit()
        await db.refresh(target_entity)
        return target_entity
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to merge entities: {e!s}") from e
