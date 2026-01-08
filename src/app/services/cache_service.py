"""
Cache service for Redis operations.

Provides caching functionality with graceful degradation
when Redis is unavailable.
"""

import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.logger import get_logger
from app.schemas.llm import CachedResult
from app.settings import Settings
from app.utils.helpers import generate_cache_key

logger = get_logger("cache_service")


class CacheService:
    """
    Cache service for storing and retrieving car pricing results.

    Uses Redis for distributed caching with configurable TTL.
    Implements graceful degradation - cache failures don't
    break the main application flow.

    Attributes:
        settings: Application settings
        redis_client: Async Redis client instance
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize cache service.

        Args:
            settings: Application settings with Redis configuration
        """
        self._settings = settings
        self._redis: redis.Redis[str] | None = None

    async def connect(self) -> None:
        """
        Establish Redis connection.

        Should be called during application startup.
        """
        try:
            self._redis = redis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            logger.info("redis_connected", extra={"url": self._settings.redis_url})
        except RedisError as e:
            logger.error(
                "redis_connection_failed",
                extra={"url": self._settings.redis_url, "error": str(e)},
            )
            self._redis = None

    async def disconnect(self) -> None:
        """
        Close Redis connection.

        Should be called during application shutdown.
        """
        if self._redis:
            await self._redis.close()
            logger.info("redis_disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._redis is not None

    async def get(self, title: str, description: str) -> CachedResult | None:
        """
        Get cached result for a car listing.

        Args:
            title: Car listing title
            description: Car listing description

        Returns:
            CachedResult if found in cache, None otherwise
        """
        if not self._redis:
            logger.debug("cache_skip_not_connected")
            return None

        cache_key = generate_cache_key(title, description)

        try:
            data = await self._redis.get(cache_key)
            if data:
                logger.debug("cache_hit", extra={"key": cache_key})
                return CachedResult.model_validate_json(data)
            else:
                logger.debug("cache_miss", extra={"key": cache_key})
                return None
        except RedisError as e:
            logger.warning("cache_get_error", extra={"key": cache_key, "error": str(e)})
            return None
        except Exception as e:
            logger.warning(
                "cache_deserialize_error", extra={"key": cache_key, "error": str(e)}
            )
            return None

    async def set(
        self,
        title: str,
        description: str,
        result: CachedResult,
    ) -> bool:
        """
        Store result in cache.

        Args:
            title: Car listing title
            description: Car listing description
            result: Result to cache

        Returns:
            bool: True if cached successfully, False otherwise
        """
        if not self._redis:
            logger.debug("cache_skip_not_connected")
            return False

        cache_key = generate_cache_key(title, description)

        try:
            await self._redis.set(
                cache_key,
                result.model_dump_json(),
                ex=self._settings.cache_ttl,
            )
            logger.debug(
                "cache_set",
                extra={"key": cache_key, "ttl": self._settings.cache_ttl},
            )
            return True
        except RedisError as e:
            logger.warning("cache_set_error", extra={"key": cache_key, "error": str(e)})
            return False

    async def delete(self, title: str, description: str) -> bool:
        """
        Delete cached result.

        Args:
            title: Car listing title
            description: Car listing description

        Returns:
            bool: True if deleted (or didn't exist), False on error
        """
        if not self._redis:
            return False

        cache_key = generate_cache_key(title, description)

        try:
            await self._redis.delete(cache_key)
            logger.debug("cache_delete", extra={"key": cache_key})
            return True
        except RedisError as e:
            logger.warning(
                "cache_delete_error", extra={"key": cache_key, "error": str(e)}
            )
            return False

    async def health_check(self) -> bool:
        """
        Check if Redis is healthy and responding.

        Returns:
            bool: True if Redis is responding, False otherwise
        """
        if not self._redis:
            return False

        try:
            await self._redis.ping()
            return True
        except RedisError:
            return False

    async def get_raw(self, key: str) -> Any:
        """
        Get raw value from Redis (for metrics).

        Args:
            key: Redis key

        Returns:
            Value if found, None otherwise
        """
        if not self._redis:
            return None

        try:
            return await self._redis.get(key)
        except RedisError:
            return None

    async def incr(self, key: str) -> int | None:
        """
        Increment a counter in Redis.

        Args:
            key: Counter key

        Returns:
            New value after increment, None on error
        """
        if not self._redis:
            return None

        try:
            return await self._redis.incr(key)
        except RedisError:
            return None

    async def zadd(
        self, key: str, score: float, member: str, ttl: int | None = None
    ) -> bool:
        """
        Add member to sorted set with score.

        Args:
            key: Sorted set key
            score: Score value
            member: Member value
            ttl: Optional TTL in seconds

        Returns:
            bool: True if added successfully
        """
        if not self._redis:
            return False

        try:
            await self._redis.zadd(key, {member: score})
            if ttl:
                await self._redis.expire(key, ttl)
            return True
        except RedisError:
            return False

    async def zrange_with_scores(
        self, key: str, start: int = 0, end: int = -1
    ) -> list[tuple[str, float]]:
        """
        Get range from sorted set with scores.

        Args:
            key: Sorted set key
            start: Start index
            end: End index (-1 for all)

        Returns:
            List of (member, score) tuples
        """
        if not self._redis:
            return []

        try:
            return await self._redis.zrange(key, start, end, withscores=True)
        except RedisError:
            return []

    async def scan_keys(self, pattern: str, count: int = 100) -> list[str]:
        """
        Scan keys matching pattern using SCAN (non-blocking).

        Uses SCAN instead of KEYS to avoid blocking Redis in production.
        KEYS command blocks Redis and should never be used in production.

        Args:
            pattern: Key pattern (e.g., 'stats:car:make:*')
            count: Hint for number of keys to return per iteration

        Returns:
            List of matching keys
        """
        if not self._redis:
            return []

        try:
            keys: list[str] = []
            async for key in self._redis.scan_iter(match=pattern, count=count):
                keys.append(key)
            return keys
        except RedisError:
            return []

    async def mget(self, keys: list[str]) -> list[Any]:
        """
        Get multiple values at once (batch operation).

        More efficient than multiple get() calls.

        Args:
            keys: List of keys to fetch

        Returns:
            List of values (None for missing keys)
        """
        if not self._redis or not keys:
            return []

        try:
            return await self._redis.mget(keys)
        except RedisError:
            return []

    async def zcard(self, key: str) -> int:
        """
        Get the number of elements in a sorted set.

        Args:
            key: Sorted set key

        Returns:
            Number of elements, 0 on error
        """
        if not self._redis:
            return 0

        try:
            return await self._redis.zcard(key)
        except RedisError:
            return 0

    async def zremrangebyrank(self, key: str, start: int, stop: int) -> int:
        """
        Remove elements from sorted set by rank (index).

        Removes all elements with rank between start and stop (inclusive).
        Rank 0 is the element with the lowest score.

        Args:
            key: Sorted set key
            start: Start rank (inclusive)
            stop: Stop rank (inclusive)

        Returns:
            Number of elements removed, 0 on error
        """
        if not self._redis:
            return 0

        try:
            return await self._redis.zremrangebyrank(key, start, stop)
        except RedisError:
            return 0
