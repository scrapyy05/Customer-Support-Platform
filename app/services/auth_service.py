import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest, TokenResponse
from app.auth.security import hash_password, verify_password
from app.auth.jwt import create_access_token, decode_token


class AuthService:
    """
    Service layer handling all user registration, authentication, and token management business logic.
    """

    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserCreate, force_customer_role: bool = True) -> User:
        """
        Registers a new user account. Checks if email is already taken.
        By default on public registration, role is forced to Customer.
        """
        query = select(User).where(User.email == user_in.email.lower())
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        role_to_assign = UserRole.CUSTOMER if force_customer_role else (user_in.role or UserRole.CUSTOMER)

        new_user = User(
            name=user_in.name,
            email=user_in.email.lower(),
            password_hash=hash_password(user_in.password),
            role=role_to_assign,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def authenticate_user(db: AsyncSession, login_in: LoginRequest) -> TokenResponse:
        """
        Verifies login credentials and issues an access token.
        """
        query = select(User).where(User.email == login_in.email.lower())
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not verify_password(login_in.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )

        access_token = create_access_token(subject=str(user.id), role=user.role.value)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user,
        )
