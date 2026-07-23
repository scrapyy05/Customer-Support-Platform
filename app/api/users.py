import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserRoleUpdate
from app.services.user_service import UserService
from app.auth.permissions import get_current_user, require_roles

router = APIRouter()


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (Admin only - allows creating Agents and Admins)",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Admin endpoint to provision accounts with specific roles such as support agents.
    """
    return await UserService.create_user_by_admin(db=db, user_in=user_in)


@router.get(
    "",
    response_model=List[UserRead],
    status_code=status.HTTP_200_OK,
    summary="List all registered users with optional role filtering (Admin only)",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    role: Optional[UserRole] = Query(None, description="Filter users by role"),
    db: AsyncSession = Depends(get_db),
):
    return await UserService.list_users(db=db, skip=skip, limit=limit, role_filter=role)


@router.get(
    "/{id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get user profile details by ID",
)
async def get_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Users can view their own profile. Admins and Agents can view any user profile.
    """
    if current_user.role == UserRole.CUSTOMER and current_user.id != id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Can only view your own profile."
        )
    return await UserService.get_user_by_id(db=db, user_id=id)


@router.patch(
    "/{id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update user profile information",
)
async def update_user(
    id: uuid.UUID,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Users can update their own name or email. Admins can update any user profile or deactivate them (`is_active`).
    """
    if current_user.role != UserRole.ADMIN and current_user.id != id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Can only update your own profile."
        )
    if user_update.is_active is not None and current_user.role != UserRole.ADMIN:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins can activate/deactivate user accounts."
        )
    return await UserService.update_user(db=db, user_id=id, user_update=user_update)


@router.patch(
    "/{id}/role",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Change user role (Admin only)",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def change_role(
    id: uuid.UUID,
    role_in: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await UserService.change_user_role(db=db, user_id=id, new_role=role_in.role)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user account (Admin only)",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def delete_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await UserService.delete_user(db=db, user_id=id)
