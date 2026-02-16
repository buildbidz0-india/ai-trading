"""Redis cache adapter implementing CachePort.

Provides key-value caching with TTL and pub/sub for live data distribution.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, Dict

import redis.asyncio as redis
import structlog

from app.ports.outbound import CachePort

logger = structlog.get_logger(__name__)


class MemoryCacheAdapter(CachePort):
    """In-memory cache falling back if Redis is unavailable."""
    
    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        logger.info("cache_initialized_memory_fallback")

    async def get(self, key: str) -> str | None:
        if key in self._expiry and self._expiry[key] < time.time():
            del self._data[key]
            del self._expiry[key]
            return None
        return self._data.get(key)

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        self._data[key] = value
        if ttl_seconds:
            self._expiry[key] = time.time() + ttl_seconds

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._expiry.pop(key, None)

    async def publish(self, channel: str, message: str) -> None:
        # Memory fallback doesn't support cross-process pub/sub
        logger.debug("mem_cache_publish_no_op", channel=channel)

    async def increment(self, key: str, *, ttl_seconds: int | None = None) -> int:
        current = int(self._data.get(key, 0))
        new_val = current + 1
        await self.set(key, str(new_val), ttl_seconds=ttl_seconds)
        return new_val

    async def subscribe(self, channel: str) -> Any:
        # This will fail for real-time features that need real pubsub
        class DummyPubSub:
            async def subscribe(self, *args: Any, **kwargs: Any) -> None: pass
            async def listen(self) -> AsyncIterator[Any]:
                yield {"type": "subscribe", "channel": channel, "data": 1}
                while True:
                    await asyncio.sleep(3600)
        return DummyPubSub()

    async def close(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True


class RedisCacheAdapter(CachePort):
    """Async Redis adapter for hot data caching and pub/sub."""

    def __init__(self, url: str, max_connections: int = 50) -> None:
        # If localhost or empty, fallback to memory immediately in non-dev environments
        is_local = "localhost" in url or "127.0.0.1" in url
        self._use_memory = not url or is_local
        
        if self._use_memory:
            logger.warning("redis_url_missing_or_local_falling_back_to_memory", url=url)
            self._memory = MemoryCacheAdapter()
            return
            
        try:
            self._pool = redis.ConnectionPool.from_url(
                url,
                max_connections=max_connections,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
        except Exception as e:
            logger.error("redis_init_failed", error=str(e))
            self._use_memory = True
            self._memory = MemoryCacheAdapter()

    async def get(self, key: str) -> str | None:
        if self._use_memory: return await self._memory.get(key)
        try:
            return await self._client.get(key)
        except redis.RedisError as exc:
            logger.error("redis_get_error", key=key, error=str(exc))
            return None

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        if self._use_memory: return await self._memory.set(key, value, ttl_seconds=ttl_seconds)
        try:
            if ttl_seconds:
                await self._client.setex(key, ttl_seconds, value)
            else:
                await self._client.set(key, value)
        except redis.RedisError as exc:
            logger.error("redis_set_error", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        if self._use_memory: return await self._memory.delete(key)
        try:
            await self._client.delete(key)
        except redis.RedisError as exc:
            logger.error("redis_delete_error", key=key, error=str(exc))

    async def publish(self, channel: str, message: str) -> None:
        if self._use_memory: return await self._memory.publish(channel, message)
        try:
            await self._client.publish(channel, message)
        except redis.RedisError as exc:
            logger.error("redis_publish_error", channel=channel, error=str(exc))

    async def increment(self, key: str, *, ttl_seconds: int | None = None) -> int:
        if self._use_memory: return await self._memory.increment(key, ttl_seconds=ttl_seconds)
        try:
            val = await self._client.incr(key)
            if ttl_seconds and val == 1:
                await self._client.expire(key, ttl_seconds)
            return val
        except redis.RedisError as exc:
            logger.error("redis_incr_error", key=key, error=str(exc))
            return 0

    async def subscribe(self, channel: str) -> Any:
        if self._use_memory: return await self._memory.subscribe(channel)
        try:
            pubsub = self._client.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except redis.RedisError as exc:
            logger.error("redis_subscribe_error", channel=channel, error=str(exc))
            raise

    async def close(self) -> None:
        if not self._use_memory:
            await self._client.aclose()
            await self._pool.aclose()

    async def health_check(self) -> bool:
        if self._use_memory: return True
        try:
            return await self._client.ping()
        except redis.RedisError:
            return False
