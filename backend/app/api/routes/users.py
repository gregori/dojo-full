"""User routes: list users, assign/remove roles."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.get_current_user import require_role
from app.api.dependencies.get_db import get_db
from app.domain.exceptions import InvalidRoleError, UserNotFoundError
from app.domain.models.user import User
from app.schemas.user import (
    RoleAssignmentRequest,
    UserListResponse,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    current_user: User = Depends(require_role("instructor", "super-admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    List users in the current user's organization.

    Requires instructor or super-admin role.
    """
    user_service = UserService(db)
    users, total = await user_service.list_users(
        org_id=current_user.org_id,
        offset=offset,
        limit=limit,
    )
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/{user_id}/roles", response_model=UserResponse)
async def assign_role(
    user_id: str,
    body: RoleAssignmentRequest,
    current_user: Annotated[User, Depends(require_role("super-admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Assign a role to a user. Only super-admin can assign roles."""
    user_service = UserService(db)

    try:
        user = await user_service.assign_role(user_id=user_id, role=body.role)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except InvalidRoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UserResponse.model_validate(user)


@router.delete("/{user_id}/roles/instructor", response_model=UserResponse)
async def remove_instructor_role(
    user_id: str,
    current_user: Annotated[User, Depends(require_role("super-admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove the instructor role from a user. Only super-admin can remove roles."""
    user_service = UserService(db)

    try:
        user = await user_service.remove_role(
            user_id=user_id, role="instructor"
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except InvalidRoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UserResponse.model_validate(user)
