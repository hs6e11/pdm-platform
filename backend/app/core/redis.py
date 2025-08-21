import redis.asyncio as redis
from app.core.config import settings

# Redis client
redis_client = None


async def get_redis_client():
    """Get Redis client."""
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(settings.REDIS_URL)
    return redis_client


async def check_redis_connection() -> bool:
    """Check Redis connection health."""
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception:
        return False
