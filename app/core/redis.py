import fakeredis.aioredis

# We use fakeredis to perfectly simulate a Redis server entirely in memory.
# When ready for production, simply change this to:
# import redis.asyncio as aioredis
# from app.core.config import settings
# redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)

async def get_redis():
    """
    Dependency that yields the Redis connection pool.
    """
    yield redis_client
