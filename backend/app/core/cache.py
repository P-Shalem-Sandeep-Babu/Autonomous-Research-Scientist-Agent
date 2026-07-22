import redis.asyncio as redis
from app.core.config import settings
from typing import Optional, Any
import json

class RedisCache:
    """Redis caching utility for the FastAPI backend."""

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.connection = None

    async def get_connection(self) -> redis.Redis:
        """Get or create a Redis connection."""
        if not self.connection:
            self.connection = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.connection

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set a key-value pair in Redis with an optional expiry (in seconds)."""
        connection = await self.get_connection()
        try:
            await connection.set(key, json.dumps(value), ex=expire)
            return True
        except Exception as e:
            print(f"Error setting cache key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get the value for a key from Redis."""
        connection = await self.get_connection()
        try:
            value = await connection.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"Error getting cache key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        connection = await self.get_connection()
        try:
            await connection.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting cache key {key}: {e}")
            return False

# Singleton instance for global use
cache = RedisCache()