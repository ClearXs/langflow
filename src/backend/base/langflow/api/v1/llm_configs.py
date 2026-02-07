"""API routes for LLMConfig CRUD operations.

LLMConfig combines LLM model settings with prompt configuration:
- LLM provider, model, API key, etc.
- Configurable system instructions
- Citation toggle
"""

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.future import select

from langflow.agents.new_chat.system_prompt import get_default_system_instructions
from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.schema import (
    DefaultSystemInstructionsResponse,
    GlobalLLMConfigRead,
)
from langflow.services.database.models.llm_config import LLMConfig, LLMConfigCreate, LLMConfigRead, LLMConfigUpdate
from langflow.services.database.models.role import Permission
from langflow.services.deps import get_settings_service
from langflow.services.llm import validate_llm_config
from langflow.utils.rbac import check_permission

router = APIRouter(prefix="/llm-configs", tags=["LLM Configs"])
logger = logging.getLogger(__name__)


# =============================================================================
# Global Configs Routes
# =============================================================================


@router.get("/global-llm-configs", response_model=list[GlobalLLMConfigRead])
@router.get("/global", response_model=list[GlobalLLMConfigRead])  # Alias for frontend compatibility
async def get_global_llm_configs(
    current_user: CurrentActiveUser = None,
):
    """Get all available global LLMConfig configurations.
    These are pre-configured by the system administrator and available to all users.
    API keys are not exposed through this endpoint.

    Global configs have negative IDs to distinguish from user-created configs.
    """
    try:
        settings_service = get_settings_service()
        config = settings_service.settings
        global_configs = config.GLOBAL_LLM_CONFIGS

        # Transform to new structure, hiding API keys
        safe_configs = []
        for cfg in global_configs:
            safe_config = {
                "id": cfg.get("id"),
                "name": cfg.get("name"),
                "description": cfg.get("description"),
                "provider": cfg.get("provider"),
                "custom_provider": cfg.get("custom_provider"),
                "model_name": cfg.get("model_name"),
                "api_base": cfg.get("api_base") or None,
                "litellm_params": cfg.get("litellm_params", {}),
                # New prompt configuration fields
                "system_instructions": cfg.get("system_instructions", ""),
                "use_default_system_instructions": cfg.get(
                    "use_default_system_instructions", True
                ),
                "citations_enabled": cfg.get("citations_enabled", True),
                "is_global": True,
            }
            safe_configs.append(safe_config)

        return safe_configs
    except Exception as e:
        logger.exception("Failed to fetch global LLMConfigs")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch global configurations: {e!s}"
        ) from e


# =============================================================================
# CRUD Routes
# =============================================================================


@router.post("/", response_model=LLMConfigRead)
async def create_llm_config(
    config_data: LLMConfigCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Create a new LLMConfig for a search space.
    Requires LLM_CONFIGS_CREATE permission.
    """
    try:
        # Verify user has permission
        await check_permission(
            db,
            current_user,
            config_data.search_space_id,
            Permission.LLM_CONFIGS_CREATE.value,
            "You don't have permission to create LLM configurations in this search space",
        )

        # Validate the LLM configuration by making a test API call
        is_valid, error_message = await validate_llm_config(
            provider=config_data.provider,
            model_name=config_data.model_name,
            api_key=config_data.api_key,
            api_base=config_data.api_base,
            custom_provider=config_data.custom_provider,
            litellm_params=config_data.litellm_params,
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid LLM configuration: {error_message}",
            )

        # Create the config
        db_config = LLMConfig(**config_data.model_dump())
        db.add(db_config)
        await db.commit()
        await db.refresh(db_config)

        return db_config

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create LLMConfig")
        raise HTTPException(
            status_code=500, detail=f"Failed to create configuration: {e!s}"
        ) from e


@router.get("/", response_model=list[LLMConfigRead])
async def list_llm_configs(
    search_space_id: int,
    skip: int = 0,
    limit: int = 100,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get all LLMConfigs for a search space.
    Requires LLM_CONFIGS_READ permission.
    """
    try:
        # Verify user has permission
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.LLM_CONFIGS_READ.value,
            "You don't have permission to view LLM configurations in this search space",
        )

        result = await db.execute(
            select(LLMConfig)
            .filter(LLMConfig.search_space_id == search_space_id)
            .order_by(LLMConfig.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list LLMConfigs")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch configurations: {e!s}"
        ) from e


@router.get(
    "/default-system-instructions",
    response_model=DefaultSystemInstructionsResponse,
)
async def get_default_system_instructions_endpoint(
    current_user: CurrentActiveUser = None,
):
    """Get the default SURFSENSE_SYSTEM_INSTRUCTIONS template.
    Useful for pre-populating the UI when creating a new configuration.
    """
    return DefaultSystemInstructionsResponse(
        default_system_instructions=get_default_system_instructions()
    )


@router.get("/{config_id}", response_model=LLMConfigRead)
async def get_llm_config(
    config_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Get a specific LLMConfig by ID.
    Requires LLM_CONFIGS_READ permission.
    """
    try:
        result = await db.execute(
            select(LLMConfig).filter(LLMConfig.id == config_id)
        )
        config = result.scalars().first()

        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Verify user has permission
        await check_permission(
            db,
            current_user,
            config.search_space_id,
            Permission.LLM_CONFIGS_READ.value,
            "You don't have permission to view LLM configurations in this search space",
        )

        return config

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get LLMConfig")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch configuration: {e!s}"
        ) from e


@router.put("/{config_id}", response_model=LLMConfigRead)
async def update_llm_config(
    config_id: int,
    update_data: LLMConfigUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Update an existing LLMConfig.
    Requires LLM_CONFIGS_UPDATE permission.
    """
    try:
        result = await db.execute(
            select(LLMConfig).filter(LLMConfig.id == config_id)
        )
        config = result.scalars().first()

        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Verify user has permission
        await check_permission(
            db,
            current_user,
            config.search_space_id,
            Permission.LLM_CONFIGS_UPDATE.value,
            "You don't have permission to update LLM configurations in this search space",
        )

        update_dict = update_data.model_dump(exclude_unset=True)

        # If updating LLM settings, validate them
        if any(
            key in update_dict
            for key in [
                "provider",
                "model_name",
                "api_key",
                "api_base",
                "custom_provider",
                "litellm_params",
            ]
        ):
            # Build the validation config from existing + updates
            validation_config = {
                "provider": update_dict.get("provider", config.provider)
                if isinstance(update_dict.get("provider", config.provider), str)
                else config.provider.value,
                "model_name": update_dict.get("model_name", config.model_name),
                "api_key": update_dict.get("api_key", config.api_key),
                "api_base": update_dict.get("api_base", config.api_base),
                "custom_provider": update_dict.get(
                    "custom_provider", config.custom_provider
                ),
                "litellm_params": update_dict.get(
                    "litellm_params", config.litellm_params
                ),
            }

            is_valid, error_message = await validate_llm_config(
                provider=validation_config["provider"],
                model_name=validation_config["model_name"],
                api_key=validation_config["api_key"],
                api_base=validation_config["api_base"],
                custom_provider=validation_config["custom_provider"],
                litellm_params=validation_config["litellm_params"],
            )

            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid LLM configuration: {error_message}",
                )

        # Apply updates
        for key, value in update_dict.items():
            setattr(config, key, value)

        await db.commit()
        await db.refresh(config)

        return config

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update LLMConfig")
        raise HTTPException(
            status_code=500, detail=f"Failed to update configuration: {e!s}"
        ) from e


@router.delete("/{config_id}", response_model=dict)
async def delete_llm_config(
    config_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """Delete a LLMConfig.
    Requires LLM_CONFIGS_DELETE permission.
    """
    try:
        result = await db.execute(
            select(LLMConfig).filter(LLMConfig.id == config_id)
        )
        config = result.scalars().first()

        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Verify user has permission
        await check_permission(
            db,
            current_user,
            config.search_space_id,
            Permission.LLM_CONFIGS_DELETE.value,
            "You don't have permission to delete LLM configurations in this search space",
        )

        await db.delete(config)
        await db.commit()

        return {"message": "Configuration deleted successfully", "id": config_id}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to delete LLMConfig")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete configuration: {e!s}"
        ) from e
