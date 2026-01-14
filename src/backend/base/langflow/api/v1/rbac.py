"""
RBAC (Role-Based Access Control) routes for managing roles, memberships, and invites.

Endpoints:
- /spaces/{search_space_id}/roles - CRUD for roles
- /spaces/{search_space_id}/members - CRUD for memberships
- /spaces/{search_space_id}/invites - CRUD for invites
- /invites/{invite_code}/info - Get invite info (public)
- /invites/accept - Accept an invite
- /permissions - List all available permissions
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.services.database.models.role import Permission, Role, RoleCreate, RoleRead, RoleUpdate
from langflow.services.database.models.space import Space
from langflow.services.database.models.space_invite import SpaceInvite, SpaceInviteCreate, SpaceInviteRead
from langflow.services.database.models.space_membership import SpaceMembership, SpaceMembershipCreate, SpaceMembershipRead
from langflow.services.database.models.user import User
from langflow.schema import (
    InviteAcceptRequest,
    InviteAcceptResponse,
    InviteInfoResponse,
    InviteUpdate,
    MembershipUpdate,
    PermissionInfo,
    PermissionsListResponse,
    UserSpaceAccess,
)
from langflow.utils.rbac import (
    check_permission,
    check_search_space_access,
    generate_invite_code,
    get_default_role,
    get_user_permissions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rbac", tags=["rbac"])


# ============ Permissions Endpoints ============


@router.get("/permissions", response_model=PermissionsListResponse)
async def list_all_permissions(
    current_user: CurrentActiveUser = None,
):
    """
    List all available permissions that can be assigned to roles.
    """
    permissions = []
    for perm in Permission:
        # Extract category from permission value (e.g., "documents:read" -> "documents")
        category = perm.value.split(":")[0] if ":" in perm.value else "general"

        permissions.append(
            PermissionInfo(
                value=perm.value,
                name=perm.name,
                category=category,
            )
        )

    return PermissionsListResponse(permissions=permissions)


# ============ Role Endpoints ============


@router.post(
    "/spaces/{search_space_id}/roles",
    response_model=RoleRead,
)
async def create_role(
    search_space_id: int,
    role_data: RoleCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Create a new custom role in a search space.
    Requires ROLES_CREATE permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.ROLES_CREATE.value,
            "You don't have permission to create roles",
        )

        # Check if role with same name already exists
        result = await db.execute(
            select(Role).filter(
                Role.search_space_id == search_space_id,
                Role.name == role_data.name,
            )
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=409,
                detail=f"A role with name '{role_data.name}' already exists in this search space",
            )

        # Validate permissions
        valid_permissions = {p.value for p in Permission}
        for perm in role_data.permissions:
            if perm not in valid_permissions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid permission: {perm}",
                )

        # If setting is_default to True, unset any existing default
        if role_data.is_default:
            await db.execute(
                select(Role).filter(
                    Role.search_space_id == search_space_id,
                    Role.is_default == True,  # noqa: E712
                )
            )
            existing_defaults = await db.execute(
                select(Role).filter(
                    Role.search_space_id == search_space_id,
                    Role.is_default == True,  # noqa: E712
                )
            )
            for existing in existing_defaults.scalars().all():
                existing.is_default = False

        db_role = Role(
            **role_data.model_dump(),
            search_space_id=search_space_id,
            is_system_role=False,
        )
        db.add(db_role)
        await db.commit()
        await db.refresh(db_role)
        return db_role

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create role: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create role: {e!s}"
        ) from e


@router.get(
    "/spaces/{search_space_id}/roles",
    response_model=list[RoleRead],
)
async def list_roles(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    List all roles in a search space.
    Requires ROLES_READ permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.ROLES_READ.value,
            "You don't have permission to view roles",
        )

        result = await db.execute(
            select(Role).filter(
                Role.search_space_id == search_space_id
            )
        )
        return result.scalars().all()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch roles: {e!s}"
        ) from e


@router.get(
    "/spaces/{search_space_id}/roles/{role_id}",
    response_model=RoleRead,
)
async def get_role(
    search_space_id: int,
    role_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Get a specific role by ID.
    Requires ROLES_READ permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.ROLES_READ.value,
            "You don't have permission to view roles",
        )

        result = await db.execute(
            select(Role).filter(
                Role.id == role_id,
                Role.search_space_id == search_space_id,
            )
        )
        role = result.scalars().first()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        return role

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch role: {e!s}"
        ) from e


@router.put(
    "/spaces/{search_space_id}/roles/{role_id}",
    response_model=RoleRead,
)
async def update_role(
    search_space_id: int,
    role_id: int,
    role_update: RoleUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Update a role.
    Requires ROLES_UPDATE permission.
    System roles can only have their permissions updated, not name/description.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.ROLES_UPDATE.value,
            "You don't have permission to update roles",
        )

        result = await db.execute(
            select(Role).filter(
                Role.id == role_id,
                Role.search_space_id == search_space_id,
            )
        )
        db_role = result.scalars().first()

        if not db_role:
            raise HTTPException(status_code=404, detail="Role not found")

        update_data = role_update.model_dump(exclude_unset=True)

        # System roles have restrictions on what can be updated
        if db_role.is_system_role:
            # Can only update permissions for system roles
            restricted_fields = {"name", "description", "is_default"}
            if any(field in update_data for field in restricted_fields):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot modify name, description, or default status of system roles",
                )

        # Check for name conflict if updating name
        if "name" in update_data and update_data["name"] != db_role.name:
            existing = await db.execute(
                select(Role).filter(
                    Role.search_space_id == search_space_id,
                    Role.name == update_data["name"],
                )
            )
            if existing.scalars().first():
                raise HTTPException(
                    status_code=409,
                    detail=f"A role with name '{update_data['name']}' already exists",
                )

        # Validate permissions if provided
        if "permissions" in update_data:
            valid_permissions = {p.value for p in Permission}
            for perm in update_data["permissions"]:
                if perm not in valid_permissions:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid permission: {perm}",
                    )

        # Handle is_default change
        if update_data.get("is_default") and not db_role.is_default:
            # Unset existing default
            existing_defaults = await db.execute(
                select(Role).filter(
                    Role.search_space_id == search_space_id,
                    Role.is_default == True,  # noqa: E712
                )
            )
            for existing in existing_defaults.scalars().all():
                existing.is_default = False

        for key, value in update_data.items():
            setattr(db_role, key, value)

        await db.commit()
        await db.refresh(db_role)
        return db_role

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update role: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update role: {e!s}"
        ) from e


@router.delete("/spaces/{search_space_id}/roles/{role_id}")
async def delete_role(
    search_space_id: int,
    role_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Delete a custom role.
    Requires ROLES_DELETE permission.
    System roles cannot be deleted.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.ROLES_DELETE.value,
            "You don't have permission to delete roles",
        )

        result = await db.execute(
            select(Role).filter(
                Role.id == role_id,
                Role.search_space_id == search_space_id,
            )
        )
        db_role = result.scalars().first()

        if not db_role:
            raise HTTPException(status_code=404, detail="Role not found")

        if db_role.is_system_role:
            raise HTTPException(
                status_code=400,
                detail="System roles cannot be deleted",
            )

        await db.delete(db_role)
        await db.commit()
        return {"message": "Role deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete role: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete role: {e!s}"
        ) from e


# ============ Membership Endpoints ============


@router.get(
    "/spaces/{search_space_id}/members",
    response_model=list[SpaceMembershipRead],
)
async def list_members(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    List all members of a search space.
    Requires MEMBERS_VIEW permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.MEMBERS_VIEW.value,
            "You don't have permission to view members",
        )

        result = await db.execute(
            select(SpaceMembership)
            .options(selectinload(SpaceMembership.role))
            .filter(SpaceMembership.search_space_id == search_space_id)
        )
        memberships = result.scalars().all()

        # Fetch user emails for each membership
        response = []
        for membership in memberships:
            user_result = await db.execute(
                select(User).filter(User.id == membership.user_id)
            )
            member_user = user_result.scalars().first()

            membership_dict = {
                "id": membership.id,
                "user_id": membership.user_id,
                "search_space_id": membership.search_space_id,
                "role_id": membership.role_id,
                "is_owner": membership.is_owner,
                "joined_at": membership.joined_at,
                "created_at": membership.created_at,
                "role": membership.role,
                "user_email": member_user.email if member_user else None,
            }
            response.append(membership_dict)

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch members: {e!s}"
        ) from e


@router.put(
    "/spaces/{search_space_id}/members/{membership_id}",
    response_model=SpaceMembershipRead,
)
async def update_member_role(
    search_space_id: int,
    membership_id: int,
    membership_update: MembershipUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Update a member's role.
    Requires MEMBERS_MANAGE_ROLES permission.
    Cannot change owner's role.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.MEMBERS_MANAGE_ROLES.value,
            "You don't have permission to manage member roles",
        )

        result = await db.execute(
            select(SpaceMembership)
            .options(selectinload(SpaceMembership.role))
            .filter(
                SpaceMembership.id == membership_id,
                SpaceMembership.search_space_id == search_space_id,
            )
        )
        db_membership = result.scalars().first()

        if not db_membership:
            raise HTTPException(status_code=404, detail="Membership not found")

        # Cannot change owner's role
        if db_membership.is_owner:
            raise HTTPException(
                status_code=400,
                detail="Cannot change the owner's role",
            )

        # Verify the new role exists in this search space
        if membership_update.role_id:
            role_result = await db.execute(
                select(Role).filter(
                    Role.id == membership_update.role_id,
                    Role.search_space_id == search_space_id,
                )
            )
            if not role_result.scalars().first():
                raise HTTPException(
                    status_code=404,
                    detail="Role not found in this search space",
                )

        db_membership.role_id = membership_update.role_id
        await db.commit()
        await db.refresh(db_membership)

        # Fetch user email
        user_result = await db.execute(
            select(User).filter(User.id == db_membership.user_id)
        )
        member_user = user_result.scalars().first()

        return {
            "id": db_membership.id,
            "user_id": db_membership.user_id,
            "search_space_id": db_membership.search_space_id,
            "role_id": db_membership.role_id,
            "is_owner": db_membership.is_owner,
            "joined_at": db_membership.joined_at,
            "created_at": db_membership.created_at,
            "role": db_membership.role,
            "user_email": member_user.email if member_user else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update member role: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update member role: {e!s}"
        ) from e


@router.delete("/spaces/{search_space_id}/members/{membership_id}")
async def remove_member(
    search_space_id: int,
    membership_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Remove a member from a search space.
    Requires MEMBERS_REMOVE permission.
    Cannot remove the owner.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.MEMBERS_REMOVE.value,
            "You don't have permission to remove members",
        )

        result = await db.execute(
            select(SpaceMembership).filter(
                SpaceMembership.id == membership_id,
                SpaceMembership.search_space_id == search_space_id,
            )
        )
        db_membership = result.scalars().first()

        if not db_membership:
            raise HTTPException(status_code=404, detail="Membership not found")

        if db_membership.is_owner:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the owner from the search space",
            )

        await db.delete(db_membership)
        await db.commit()
        return {"message": "Member removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to remove member: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to remove member: {e!s}"
        ) from e


@router.delete("/spaces/{search_space_id}/members/me")
async def leave_search_space(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Leave a search space (remove own membership).
    Owners cannot leave their search space.
    """
    try:
        result = await db.execute(
            select(SpaceMembership).filter(
                SpaceMembership.user_id == current_user.id,
                SpaceMembership.search_space_id == search_space_id,
            )
        )
        db_membership = result.scalars().first()

        if not db_membership:
            raise HTTPException(
                status_code=404,
                detail="You are not a member of this search space",
            )

        if db_membership.is_owner:
            raise HTTPException(
                status_code=400,
                detail="Owners cannot leave their search space. Transfer ownership first or delete the search space.",
            )

        await db.delete(db_membership)
        await db.commit()
        return {"message": "Successfully left the search space"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to leave search space: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to leave search space: {e!s}"
        ) from e


# ============ Invite Endpoints ============


@router.post(
    "/spaces/{search_space_id}/invites",
    response_model=SpaceInviteRead,
)
async def create_invite(
    search_space_id: int,
    invite_data: SpaceInviteCreate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Create a new invite link for a search space.
    Requires MEMBERS_INVITE permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.MEMBERS_INVITE.value,
            "You don't have permission to create invites",
        )

        # Verify role exists if specified
        if invite_data.role_id:
            role_result = await db.execute(
                select(Role).filter(
                    Role.id == invite_data.role_id,
                    Role.search_space_id == search_space_id,
                )
            )
            if not role_result.scalars().first():
                raise HTTPException(
                    status_code=404,
                    detail="Role not found in this search space",
                )

        db_invite = SpaceInvite(
            **invite_data.model_dump(),
            invite_code=generate_invite_code(),
            search_space_id=search_space_id,
            created_by_id=current_user.id,
        )
        db.add(db_invite)
        await db.commit()

        # Reload with role
        result = await db.execute(
            select(SpaceInvite)
            .options(selectinload(SpaceInvite.role))
            .filter(SpaceInvite.id == db_invite.id)
        )
        db_invite = result.scalars().first()

        return db_invite

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create invite: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create invite: {e!s}"
        ) from e


@router.get(
    "/spaces/{search_space_id}/invites",
    response_model=list[SpaceInviteRead],
)
async def list_invites(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    List all invites for a search space.
    Requires MEMBERS_INVITE permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.MEMBERS_INVITE.value,
            "You don't have permission to view invites",
        )

        result = await db.execute(
            select(SpaceInvite)
            .options(selectinload(SpaceInvite.role))
            .filter(SpaceInvite.search_space_id == search_space_id)
        )
        return result.scalars().all()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch invites: {e!s}"
        ) from e


@router.put(
    "/spaces/{search_space_id}/invites/{invite_id}",
    response_model=SpaceInviteRead,
)
async def update_invite(
    search_space_id: int,
    invite_id: int,
    invite_update: InviteUpdate,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Update an invite.
    Requires MEMBERS_INVITE permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.MEMBERS_INVITE.value,
            "You don't have permission to update invites",
        )

        result = await db.execute(
            select(SpaceInvite)
            .options(selectinload(SpaceInvite.role))
            .filter(
                SpaceInvite.id == invite_id,
                SpaceInvite.search_space_id == search_space_id,
            )
        )
        db_invite = result.scalars().first()

        if not db_invite:
            raise HTTPException(status_code=404, detail="Invite not found")

        update_data = invite_update.model_dump(exclude_unset=True)

        # Verify role exists if updating role_id
        if update_data.get("role_id"):
            role_result = await db.execute(
                select(Role).filter(
                    Role.id == update_data["role_id"],
                    Role.search_space_id == search_space_id,
                )
            )
            if not role_result.scalars().first():
                raise HTTPException(
                    status_code=404,
                    detail="Role not found in this search space",
                )

        for key, value in update_data.items():
            setattr(db_invite, key, value)

        await db.commit()
        await db.refresh(db_invite)
        return db_invite

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update invite: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update invite: {e!s}"
        ) from e


@router.delete("/spaces/{search_space_id}/invites/{invite_id}")
async def revoke_invite(
    search_space_id: int,
    invite_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Revoke (delete) an invite.
    Requires MEMBERS_INVITE permission.
    """
    try:
        await check_permission(
            db,
            current_user,
            search_space_id,
            Permission.MEMBERS_INVITE.value,
            "You don't have permission to revoke invites",
        )

        result = await db.execute(
            select(SpaceInvite).filter(
                SpaceInvite.id == invite_id,
                SpaceInvite.search_space_id == search_space_id,
            )
        )
        db_invite = result.scalars().first()

        if not db_invite:
            raise HTTPException(status_code=404, detail="Invite not found")

        await db.delete(db_invite)
        await db.commit()
        return {"message": "Invite revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to revoke invite: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to revoke invite: {e!s}"
        ) from e


# ============ Public Invite Endpoints ============


@router.get("/invites/{invite_code}/info", response_model=InviteInfoResponse)
async def get_invite_info(
    invite_code: str,
    db: DbSession = None,
):
    """
    Get information about an invite (public endpoint, no auth required).
    Returns minimal info for displaying on invite acceptance page.
    """
    try:
        result = await db.execute(
            select(SpaceInvite)
            .options(
                selectinload(SpaceInvite.role),
                selectinload(SpaceInvite.search_space),
            )
            .filter(SpaceInvite.invite_code == invite_code)
        )
        invite = result.scalars().first()

        if not invite:
            return InviteInfoResponse(
                search_space_name="",
                role_name=None,
                is_valid=False,
                message="Invite not found",
            )

        # Check if invite is still valid
        if not invite.is_active:
            return InviteInfoResponse(
                search_space_name=invite.search_space.name
                if invite.search_space
                else "",
                role_name=invite.role.name if invite.role else None,
                is_valid=False,
                message="This invite is no longer active",
            )

        if invite.expires_at and invite.expires_at < datetime.now(UTC):
            return InviteInfoResponse(
                search_space_name=invite.search_space.name
                if invite.search_space
                else "",
                role_name=invite.role.name if invite.role else None,
                is_valid=False,
                message="This invite has expired",
            )

        if invite.max_uses and invite.uses_count >= invite.max_uses:
            return InviteInfoResponse(
                search_space_name=invite.search_space.name
                if invite.search_space
                else "",
                role_name=invite.role.name if invite.role else None,
                is_valid=False,
                message="This invite has reached its maximum uses",
            )

        return InviteInfoResponse(
            search_space_name=invite.search_space.name if invite.search_space else "",
            role_name=invite.role.name if invite.role else "Default",
            is_valid=True,
        )

    except Exception as e:
        logger.error(f"Failed to get invite info: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get invite info: {e!s}"
        ) from e


@router.post("/invites/accept", response_model=InviteAcceptResponse)
async def accept_invite(
    request: InviteAcceptRequest,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Accept an invite and join a search space.
    """
    try:
        result = await db.execute(
            select(SpaceInvite)
            .options(
                selectinload(SpaceInvite.role),
                selectinload(SpaceInvite.search_space),
            )
            .filter(SpaceInvite.invite_code == request.invite_code)
        )
        invite = result.scalars().first()

        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found")

        # Validate invite
        if not invite.is_active:
            raise HTTPException(
                status_code=400, detail="This invite is no longer active"
            )

        if invite.expires_at and invite.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=400, detail="This invite has expired")

        if invite.max_uses and invite.uses_count >= invite.max_uses:
            raise HTTPException(
                status_code=400, detail="This invite has reached its maximum uses"
            )

        # Check if user is already a member
        existing_membership = await db.execute(
            select(SpaceMembership).filter(
                SpaceMembership.user_id == current_user.id,
                SpaceMembership.search_space_id == invite.search_space_id,
            )
        )
        if existing_membership.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="You are already a member of this search space",
            )

        # Determine role to assign
        role_id = invite.role_id
        if not role_id:
            # Use default role
            default_role = await get_default_role(db, invite.search_space_id)
            role_id = default_role.id if default_role else None

        # Create membership
        membership = SpaceMembership(
            user_id=current_user.id,
            search_space_id=invite.search_space_id,
            role_id=role_id,
            is_owner=False,
            invited_by_invite_id=invite.id,
        )
        db.add(membership)

        # Increment invite usage
        invite.uses_count += 1

        await db.commit()

        role_name = invite.role.name if invite.role else "Default"
        search_space_name = invite.search_space.name if invite.search_space else ""

        return InviteAcceptResponse(
            message="Successfully joined the search space",
            search_space_id=invite.search_space_id,
            search_space_name=search_space_name,
            role_name=role_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to accept invite: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to accept invite: {e!s}"
        ) from e


# ============ User Access Info ============


@router.get(
    "/spaces/{search_space_id}/my-access",
    response_model=UserSpaceAccess,
)
async def get_my_access(
    search_space_id: int,
    db: DbSession = None,
    current_user: CurrentActiveUser = None,
):
    """
    Get the current user's access info for a search space.
    """
    try:
        membership = await check_search_space_access(db, current_user, search_space_id)

        # Get search space name
        result = await db.execute(
            select(Space).filter(Space.id == search_space_id)
        )
        search_space = result.scalars().first()

        # Get permissions
        permissions = await get_user_permissions(db, current_user.id, search_space_id)

        return UserSpaceAccess(
            search_space_id=search_space_id,
            search_space_name=search_space.name if search_space else "",
            is_owner=membership.is_owner,
            role_name=membership.role.name if membership.role else None,
            permissions=permissions,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get access info: {e!s}"
        ) from e
