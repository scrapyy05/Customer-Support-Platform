import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.auth.security import hash_password


class UserService:
    """
    Service layer for administrative user management, profile updates, and role assignments.
    """

    @staticmethod
    async def list_users(
        db: AsyncSession, skip: int = 0, limit: int = 100, role_filter: Optional[UserRole] = None
    ) -> List[User]:
        query = select(User).offset(skip).limit(limit)
        if role_filter:
            query = query.where(User.role == role_filter)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    @staticmethod
    async def create_user_by_admin(db: AsyncSession, user_in: UserCreate) -> User:
        """
        Admin-only creation method capable of setting explicit roles (e.g., creating Agents or Admins).
        """
        query = select(User).where(User.email == user_in.email.lower())
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered."
            )

        new_user = User(
            name=user_in.name,
            email=user_in.email.lower(),
            password_hash=hash_password(user_in.password),
            role=user_in.role or UserRole.CUSTOMER,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: uuid.UUID, user_update: UserUpdate) -> User:
        
        user = await UserService.get_user_by_id(db, user_id)

        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            user.password_hash = hash_password(update_data.pop("password"))
        if "email" in update_data and update_data["email"]:
            new_email = update_data["email"].lower()
            if new_email != user.email:
                email_check = await db.execute(select(User).where(User.email == new_email))
                if email_check.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use."
                    )
                user.email = new_email
            update_data.pop("email")

        for field, value in update_data.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_user_role(db: AsyncSession, user_id: uuid.UUID, new_role: UserRole) -> User:
        user = await UserService.get_user_by_id(db, user_id)
        user.role = new_role
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> None:
        user = await UserService.get_user_by_id(db, user_id)
        user.is_active = False
        await db.commit()
