import hashlib
import json

import redis.asyncio as redis

from app.config import settings

_client: redis.Redis | None = None


async def connect() -> None:
    global _client
    _client = redis.from_url(settings.redis_url, decode_responses=True)


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
    return await _client.get(_cache_key(prefix, payload))


async def set_cached(prefix: str, payload: dict, value: str) -> None:
    if not _client:
        return
    await _client.setex(
        _cache_key(prefix, payload),
        settings.cache_ttl_seconds,
        value,
    )
