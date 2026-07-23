import json
import uuid
from typing import Any, Optional
from app.core.redis import redis_client


class CacheService:
    """
    Centralized caching service wrapping Redis operations.
    """

    @staticmethod
    async def get_cache(key: str) -> Optional[str]:
        """
        Retrieves a string value from Redis by key.
        Returns None if the key does not exist.
        """
        data = await redis_client.get(key)
        if data is not None:
            return data
        return None
    @staticmethod
    async def set_cache(key: str, value: str, expire_seconds: int) -> None:
        """
        Stores a string value in Redis with an expiration.
        """
        await redis_client.set(key, value, ex=expire_seconds)

    @staticmethod
    async def delete_cache(key: str) -> None:
        """
        Deletes a specific key from Redis.
        """
        await redis_client.delete(key)


