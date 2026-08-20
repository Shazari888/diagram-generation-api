import hashlib
import json

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import settings

_client: redis.Redis | None = None


async def connect() -> None:
    global _client
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
        _client = client
    except RedisError:
        _client = None


async def disconnect() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None


def _cache_key(prefix: str, payload: dict) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"{prefix}:{digest}"


async def get_cached(prefix: str, payload: dict) -> str | None:
    if not _client:
        return None
    try:
        return await _client.get(_cache_key(prefix, payload))
    except RedisError:
        return None


async def increment_counter(key: str, window_seconds: int) -> int:
    """Increment a Redis counter and set its TTL on first increment. Returns current count, or 0 on error."""
    if not _client:
        return 0
    try:
        count = await _client.incr(key)
        if count == 1:
            await _client.expire(key, window_seconds)
        return count
    except RedisError:
        return 0
    if not _client:
        return
    try:
        await _client.setex(
            _cache_key(prefix, payload),
            settings.cache_ttl_seconds,
            value,
        )
    except RedisError:
        return
