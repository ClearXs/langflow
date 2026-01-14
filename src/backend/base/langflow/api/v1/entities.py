"""Entities API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.schema import PaginatedResponse
from langflow.services.database.models import Space
from langflow.services.database.models.entity import (
    Entity,
    EntityCreate,
    EntityRead,
    EntityUpdate,
    create_entity,
    delete_entity,
    get_entities_by_document,
    get_entities_by_space,
    get_entity_by_id,
    merge_entities as merge_entities_crud,
    search_entities_by_name,
    update_entity,
)
from langflow.services.database.models.role import Permission
from langflow.utils.rbac import check_permission

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("/", response_model=EntityRead)
async def create_entity_endpoint(
    entity_data: EntityCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Create a new entity.

    Requires DOCUMENTS_CREATE permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            entity_data.space_id,
            Permission.DOCUMENTS_CREATE.value,
            "You do not have permission to create entities in this space",
        )

        entity = await create_entity(db, entity_data)
        await db.commit()
        await db.refresh(entity)

        return entity

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create entity: {e!s}") from e


@router.get("/", response_model=PaginatedResponse[EntityRead])
async def list_entities(
    space_id: int,
    entity_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """List entities in a space.

    Args:
        space_id: Space ID
        entity_type: Optional entity type filter
        search: Optional name search query
        page: Page number (starting from 1)
        page_size: Items per page

    Requires DOCUMENTS_READ permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            space_id,
            Permission.DOCUMENTS_READ.value,
            "You do not have permission to read entities in this space",
        )

        # Calculate offset
        offset = (page - 1) * page_size

        # If search query exists, use search
        if search:
            entities = await search_entities_by_name(
                db, space_id, search, limit=page_size
            )
            total_count = len(entities)
        else:
            entities = await get_entities_by_space(
                db,
                space_id,
                entity_type=entity_type,
                limit=page_size,
                offset=offset,
            )

            # Get total count (simplified version, should query count in production)
            all_entities = await get_entities_by_space(
                db, space_id, entity_type=entity_type, limit=10000, offset=0
            )
            total_count = len(all_entities)

        return PaginatedResponse(
            items=entities,
            page=page,
            page_size=page_size,
            total_count=total_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get entity list: {e!s}") from e


@router.get("/{entity_id}", response_model=EntityRead)
async def get_entity(
    entity_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get entity details.

    Requires DOCUMENTS_READ permission.
    """
    try:
        entity = await get_entity_by_id(db, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Check permission
        await check_permission(
            db,
            current_user,
            entity.space_id,
            Permission.DOCUMENTS_READ.value,
            "You do not have permission to read this entity",
        )

        return entity

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get entity: {e!s}") from e


@router.put("/{entity_id}", response_model=EntityRead)
async def update_entity_endpoint(
    entity_id: int,
    entity_data: EntityUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Update entity.

    Requires DOCUMENTS_UPDATE permission.
    """
    try:
        # Get entity first to check permission
        existing_entity = await get_entity_by_id(db, entity_id)
        if not existing_entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Check permission
        await check_permission(
            db,
            current_user,
            existing_entity.space_id,
            Permission.DOCUMENTS_UPDATE.value,
            "You do not have permission to update this entity",
        )

        entity = await update_entity(db, entity_id, entity_data)
        return entity

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update entity: {e!s}") from e


@router.delete("/{entity_id}")
async def delete_entity_endpoint(
    entity_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Delete entity.

    Requires DOCUMENTS_DELETE permission.
    """
    try:
        # Get entity first to check permission
        entity = await get_entity_by_id(db, entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Check permission
        await check_permission(
            db,
            current_user,
            entity.space_id,
            Permission.DOCUMENTS_DELETE.value,
            "You do not have permission to delete this entity",
        )

        await delete_entity(db, entity_id)
        return {"message": "Entity deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete entity: {e!s}") from e


@router.post("/{entity_id}/merge/{target_entity_id}", response_model=EntityRead)
async def merge_entities_endpoint(
    entity_id: int,
    target_entity_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Merge one entity into another entity.

    Requires DOCUMENTS_UPDATE permission.
    """
    try:
        # Get source and target entities
        source_entity = await get_entity_by_id(db, entity_id)
        target_entity = await get_entity_by_id(db, target_entity_id)

        if not source_entity:
            raise HTTPException(status_code=404, detail="Source entity not found")
        if not target_entity:
            raise HTTPException(status_code=404, detail="Target entity not found")

        # Check permission (both entities must be in the same space)
        if source_entity.space_id != target_entity.space_id:
            raise HTTPException(status_code=400, detail="Entities must be in the same space")

        await check_permission(
            db,
            current_user,
            source_entity.space_id,
            Permission.DOCUMENTS_UPDATE.value,
            "You do not have permission to merge entities",
        )

        # Execute merge
        merged_entity = await merge_entities_crud(db, entity_id, target_entity_id)
        return merged_entity

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to merge entities: {e!s}") from e


@router.get("/document/{document_id}", response_model=list[EntityRead])
async def get_entities_by_document_endpoint(
    document_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get all entities extracted from a document.

    Requires DOCUMENTS_READ permission.
    """
    try:
        entities = await get_entities_by_document(db, document_id)

        if entities:
            # Check permission (using space_id from first entity)
            await check_permission(
                db,
                current_user,
                entities[0].space_id,
                Permission.DOCUMENTS_READ.value,
                "You do not have permission to read entities from this document",
            )

        return entities

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get document entities: {e!s}"
        ) from e
