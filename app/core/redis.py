import redis.asyncio as aioredis
from app.core.config import settings

# Initialize the async Redis client using the application settings
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis():
    """
    Dependency that yields the Redis connection pool.
    """
    yield redis_client
