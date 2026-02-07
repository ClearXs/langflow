import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.schema import (
    LLMPreferencesRead,
    LLMPreferencesUpdate,
    SpaceWithStats,
)
from langflow.services.database.models.llm_config import LLMConfig
from langflow.services.database.models.role import DEFAULT_ROLE_PERMISSIONS, Permission, Role
from langflow.services.database.models.space import Space, SpaceCreate, SpaceRead, SpaceUpdate
from langflow.services.database.models.space_membership import SpaceMembership
from langflow.services.deps import get_settings_service
from langflow.utils.rbac import check_permission, check_search_space_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spaces", tags=["spaces"])


async def create_default_roles_and_membership(
    session: AsyncSession,
    search_space_id: int,
    owner_user_id,
) -> None:
    """Create default system roles for a search space and add the owner as a member.

    Args:
        session: Database session
        search_space_id: The ID of the newly created search space
        owner_user_id: The UUID of the user who created the search space
    """
    # Create default roles from DEFAULT_ROLE_PERMISSIONS
    owner_role_id = None

    for role_name, permissions in DEFAULT_ROLE_PERMISSIONS.items():
        # Determine if this is the default role (Owner in this case)
        is_default = role_name == "Owner"

        db_role = Role(
            name=role_name,
            description=f"Default {role_name} role",
            permissions=permissions,
            is_default=is_default,
            is_system_role=True,
            search_space_id=search_space_id,
        )
        session.add(db_role)
        await session.flush()  # Get the ID

        if role_name == "Owner":
            owner_role_id = db_role.id

    # Create owner membership
    owner_membership = SpaceMembership(
        user_id=owner_user_id,
        space_id=search_space_id,  # Fixed: use space_id instead of search_space_id
        role_id=owner_role_id,
    )
    session.add(owner_membership)


@router.post("/", response_model=SpaceRead)
async def create_search_space(
    search_space: SpaceCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    try:
        search_space_data = search_space.model_dump()

        db_search_space = Space(**search_space_data, user_id=current_user.id)
        db.add(db_search_space)
        await db.flush()  # Get the search space ID

        # Create default roles and owner membership
        await create_default_roles_and_membership(db, db_search_space.id, current_user.id)

        await db.commit()
        await db.refresh(db_search_space)

        # Ensure settings is always a dict (handle None values)
        if db_search_space.settings is None:
            db_search_space.settings = {}

        return db_search_space
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create search space: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create search space: {e!s}"
        ) from e


@router.get("/", response_model=list[SpaceWithStats])
async def read_search_spaces(
    skip: int = 0,
    limit: int = 200,
    owned_only: bool = False,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get all search spaces the user has access to, with member count and ownership info.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        owned_only: If True, only return search spaces owned by the user.
                   If False (default), return all search spaces the user has access to.
    """
    try:
        if owned_only:
            # Return only search spaces where user is the original creator (user_id)
            result = await db.execute(
                select(Space)
                .filter(Space.user_id == current_user.id)
                .offset(skip)
                .limit(limit)
            )
            search_spaces = result.scalars().all()
        else:
            # Return all search spaces the user has membership in
            # Use a subquery to avoid JOIN issues with lazy loading
            subquery = (
                select(SpaceMembership.space_id)
                .filter(SpaceMembership.user_id == current_user.id)
                .scalar_subquery()
            )
            result = await db.execute(
                select(Space)
                .filter(Space.id.in_(subquery))
                .offset(skip)
                .limit(limit)
            )
            search_spaces = result.scalars().all()

        # Get member counts and ownership info for each search space
        search_spaces_with_stats = []
        for space in search_spaces:
            # Get member count
            count_result = await db.execute(
                select(func.count(SpaceMembership.id)).filter(
                    SpaceMembership.space_id == space.id  # Fixed: use space_id
                )
            )
            member_count = count_result.scalar() or 1

            # Get document count (placeholder - implement when Document model is ready)
            document_count = 0

            # Get connector count (placeholder - implement when Connector model is ready)
            connector_count = 0

            # Convert space to dict first, then to SpaceRead to avoid lazy loading
            space_dict = {
                "id": space.id,
                "user_id": space.user_id,
                "name": space.name,
                "description": space.description,
                "settings": space.settings if space.settings is not None else {},
                "agent_llm_id": space.agent_llm_id,
                "document_summary_llm_id": space.document_summary_llm_id,
                "citations_enabled": space.citations_enabled,
                "qna_custom_instructions": space.qna_custom_instructions,
                "enable_knowledge_graph": space.enable_knowledge_graph,
                "auto_entity_extraction": space.auto_entity_extraction,
                "graph_llm_id": space.graph_llm_id,
                "created_at": space.created_at,
                "updated_at": space.updated_at,
            }
            space_read = SpaceRead(**space_dict)

            search_spaces_with_stats.append(
                SpaceWithStats(
                    space=space_read,
                    document_count=document_count,
                    connector_count=connector_count,
                    member_count=member_count,
                )
            )

        return search_spaces_with_stats
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch search spaces: {e!s}"
        ) from e


@router.get("/{search_space_id}", response_model=SpaceRead)
async def read_search_space(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get a specific search space by ID.
    Requires SETTINGS_VIEW permission or membership.
    """
    try:
        # Check if user has access (is a member)
        await check_search_space_access(db, current_user, search_space_id)

        result = await db.execute(
            select(Space).filter(Space.id == search_space_id)
        )
        search_space = result.scalars().first()

        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found")

        # Ensure settings is always a dict (handle legacy None values)
        if search_space.settings is None:
            search_space.settings = {}

        return search_space

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch search space: {e!s}"
        ) from e


@router.put("/{search_space_id}", response_model=SpaceRead)
async def update_search_space(
    search_space_id: int,
    search_space_update: SpaceUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Update a search space.
    Requires SPACES_UPDATE permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.SPACES_UPDATE.value,
            "You don't have permission to update this search space",
        )

        result = await db.execute(
            select(Space).filter(Space.id == search_space_id)
        )
        db_search_space = result.scalars().first()

        if not db_search_space:
            raise HTTPException(status_code=404, detail="Search space not found")

        update_data = search_space_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_search_space, key, value)
        await db.commit()
        await db.refresh(db_search_space)

        # Ensure settings is always a dict (handle legacy None values)
        if db_search_space.settings is None:
            db_search_space.settings = {}

        return db_search_space
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to update search space: {e!s}"
        ) from e


@router.delete("/{search_space_id}", response_model=dict)
async def delete_search_space(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Delete a search space.
    Requires SETTINGS_DELETE permission (only owners have this by default).
    """
    try:
        # Check permission - only those with SETTINGS_DELETE can delete
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.SETTINGS_DELETE.value,
            "You don't have permission to delete this search space",
        )

        result = await db.execute(
            select(Space).filter(Space.id == search_space_id)
        )
        db_search_space = result.scalars().first()

        if not db_search_space:
            raise HTTPException(status_code=404, detail="Search space not found")

        await db.delete(db_search_space)
        await db.commit()
        return {"message": "Search space deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete search space: {e!s}"
        ) from e


# =============================================================================
# LLM Preferences Routes
# =============================================================================


async def _get_llm_config_by_id(
    session: AsyncSession, config_id: int | None, settings_service: Any
) -> dict | None:
    """Get an LLM config by ID as a dictionary. Returns database config for positive IDs,
    global config for negative IDs, or None if ID is None.
    """
    if config_id is None:
        return None

    if config_id < 0:
        # Global config - find from settings
        global_configs = settings_service.settings.GLOBAL_LLM_CONFIGS
        for cfg in global_configs:
            if cfg.get("id") == config_id:
                return {
                    "id": cfg.get("id"),
                    "name": cfg.get("name"),
                    "description": cfg.get("description"),
                    "provider": cfg.get("provider"),
                    "custom_provider": cfg.get("custom_provider"),
                    "model_name": cfg.get("model_name"),
                    "api_base": cfg.get("api_base"),
                    "litellm_params": cfg.get("litellm_params", {}),
                    "system_instructions": cfg.get("system_instructions", ""),
                    "use_default_system_instructions": cfg.get(
                        "use_default_system_instructions", True
                    ),
                    "citations_enabled": cfg.get("citations_enabled", True),
                    "is_global": True,
                }
        return None
    # Database config - convert to dict
    result = await session.execute(
        select(LLMConfig).filter(LLMConfig.id == config_id)
    )
    db_config = result.scalars().first()
    if db_config:
        return {
            "id": db_config.id,
            "name": db_config.name,
            "description": db_config.description,
            "provider": db_config.provider.value if db_config.provider else None,
            "custom_provider": db_config.custom_provider,
            "model_name": db_config.model_name,
            "api_key": db_config.api_key,
            "api_base": db_config.api_base,
            "litellm_params": db_config.litellm_params or {},
            "system_instructions": db_config.system_instructions or "",
            "use_default_system_instructions": db_config.use_default_system_instructions,
            "citations_enabled": db_config.citations_enabled,
            "created_at": db_config.created_at.isoformat()
            if db_config.created_at
            else None,
            "search_space_id": db_config.search_space_id,
        }
    return None


@router.get(
    "/{search_space_id}/llm-preferences",
    response_model=LLMPreferencesRead,
)
async def get_llm_preferences(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get LLM preferences (role assignments) for a search space.
    Requires LLM_CONFIGS_READ permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.LLM_CONFIGS_READ.value,
            "You don't have permission to view LLM preferences",
        )

        result = await db.execute(
            select(Space).filter(Space.id == search_space_id)
        )
        search_space = result.scalars().first()

        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found")

        # Get settings service
        settings_service = get_settings_service()

        # Get full config objects for each role
        agent_llm = await _get_llm_config_by_id(db, search_space.agent_llm_id, settings_service)
        document_summary_llm = await _get_llm_config_by_id(
            db, search_space.document_summary_llm_id, settings_service
        )

        return LLMPreferencesRead(
            agent_llm_id=search_space.agent_llm_id,
            document_summary_llm_id=search_space.document_summary_llm_id,
            agent_llm=agent_llm,
            document_summary_llm=document_summary_llm,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get LLM preferences")
        raise HTTPException(
            status_code=500, detail=f"Failed to get LLM preferences: {e!s}"
        ) from e


@router.put(
    "/{search_space_id}/llm-preferences",
    response_model=LLMPreferencesRead,
)
async def update_llm_preferences(
    search_space_id: int,
    preferences: LLMPreferencesUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Update LLM preferences (role assignments) for a search space.
    Requires LLM_CONFIGS_UPDATE permission.
    """
    try:
        # Check permission
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.LLM_CONFIGS_UPDATE.value,
            "You don't have permission to update LLM preferences",
        )

        result = await db.execute(
            select(Space).filter(Space.id == search_space_id)
        )
        search_space = result.scalars().first()

        if not search_space:
            raise HTTPException(status_code=404, detail="Search space not found")

        # Update preferences
        update_data = preferences.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(search_space, key, value)

        await db.commit()
        await db.refresh(search_space)

        # Get settings service
        settings_service = get_settings_service()

        # Get full config objects for response
        agent_llm = await _get_llm_config_by_id(db, search_space.agent_llm_id, settings_service)
        document_summary_llm = await _get_llm_config_by_id(
            db, search_space.document_summary_llm_id, settings_service
        )

        return LLMPreferencesRead(
            agent_llm_id=search_space.agent_llm_id,
            document_summary_llm_id=search_space.document_summary_llm_id,
            agent_llm=agent_llm,
            document_summary_llm=document_summary_llm,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update LLM preferences")
        raise HTTPException(
            status_code=500, detail=f"Failed to update LLM preferences: {e!s}"
        ) from e
