"""Redis cache adapter implementing CachePort.

Provides key-value caching with TTL and pub/sub for live data distribution.
"""

from __future__ import annotations

import redis.asyncio as redis
import structlog

from app.ports.outbound import CachePort

logger = structlog.get_logger(__name__)


class RedisCacheAdapter(CachePort):
    """Async Redis adapter for hot data caching and pub/sub."""

    def __init__(self, url: str, max_connections: int = 50) -> None:
        self._pool = redis.ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            decode_responses=True,
        )
        self._client: redis.Redis = redis.Redis(connection_pool=self._pool)  # type: ignore[type-arg]

    async def get(self, key: str) -> str | None:
        try:
            value = await self._client.get(key)
            return value  # type: ignore[return-value]
        except redis.RedisError as exc:
            logger.error("redis_get_error", key=key, error=str(exc))
            return None

    async def set(
        self, key: str, value: str, *, ttl_seconds: int | None = None
    ) -> None:
        try:
            if ttl_seconds:
                await self._client.setex(key, ttl_seconds, value)
            else:
                await self._client.set(key, value)
        except redis.RedisError as exc:
            logger.error("redis_set_error", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except redis.RedisError as exc:
            logger.error("redis_delete_error", key=key, error=str(exc))

    async def publish(self, channel: str, message: str) -> None:
        try:
            await self._client.publish(channel, message)
        except redis.RedisError as exc:
            logger.error("redis_publish_error", channel=channel, error=str(exc))

    async def increment(self, key: str, *, ttl_seconds: int | None = None) -> int:
        try:
            val = await self._client.incr(key)
            if ttl_seconds and val == 1:
                await self._client.expire(key, ttl_seconds)
            return val  # type: ignore[return-value]
        except redis.RedisError as exc:
            logger.error("redis_incr_error", key=key, error=str(exc))
            return 0

    async def close(self) -> None:
        await self._client.aclose()
        await self._pool.aclose()

    async def health_check(self) -> bool:
        try:
            return await self._client.ping()  # type: ignore[return-value]
        except redis.RedisError:
            return False
