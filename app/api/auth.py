from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account",
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Public endpoint to register a new user account. Role defaults to 'customer'.
    """
    return await AuthService.register_user(db=db, user_in=user_in, force_customer_role=True)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password to obtain JWT access token",
)
async def login(login_in: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Verifies user credentials and returns an access token.
    """
    return await AuthService.authenticate_user(db=db, login_in=login_in)
