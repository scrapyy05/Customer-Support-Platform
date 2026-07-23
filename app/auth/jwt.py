import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import jwt
from fastapi import HTTPException, status
from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(subject: str, role: str) -> str:
    """
    Creates a short-lived JWT access token containing the user ID (subject) and role.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "role": str(role),
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token 


def create_refresh_token(subject: str) -> tuple[str, datetime]:
    """
    Creates a long-lived JWT refresh token and returns both the raw token string and its expiration datetime.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(subject),
        "jti": str(uuid.uuid4()),  # Unique token ID to prevent reuse
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token. Raises 401 Unauthorized if expired or invalid.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
