"""
Redis cache with in-memory LRU fallback.

Used for cross-request analysis deduplication keyed by content hash.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

from backend.utils.performance_config import REDIS_TTL_SEC, REDIS_URL

logger = logging.getLogger("ai_forge.redis_cache")

_MEMORY: OrderedDict[str, tuple[float, str]] = OrderedDict()
_MEMORY_LOCK = threading.Lock()
_MEMORY_MAX = 256
_REDIS_CLIENT = None
_REDIS_AVAILABLE: Optional[bool] = None


def _get_redis():
    global _REDIS_CLIENT, _REDIS_AVAILABLE
    if _REDIS_AVAILABLE is False:
        return None
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    try:
        import redis
        client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=0.5)
        client.ping()
        _REDIS_CLIENT = client
        _REDIS_AVAILABLE = True
        logger.info("Redis cache connected: %s", REDIS_URL.split("@")[-1])
        return _REDIS_CLIENT
    except Exception as exc:
        _REDIS_AVAILABLE = False
        logger.info("Redis unavailable, using in-memory cache: %s", exc)
        return None


def _memory_get(key: str) -> Optional[str]:
    with _MEMORY_LOCK:
        entry = _MEMORY.get(key)
        if not entry:
            return None
        expires, value = entry
        if expires < time.time():
            del _MEMORY[key]
            return None
        _MEMORY.move_to_end(key)
        return value


def _memory_set(key: str, value: str, ttl: int) -> None:
    with _MEMORY_LOCK:
        _MEMORY[key] = (time.time() + ttl, value)
        _MEMORY.move_to_end(key)
        while len(_MEMORY) > _MEMORY_MAX:
            _MEMORY.popitem(last=False)


class RedisCache:
    """JSON-serializable cache layer."""

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raw = None
        client = _get_redis()
        if client:
            try:
                raw = client.get(key)
            except Exception as exc:
                logger.warning("Redis get failed: %s", exc)
        if raw is None:
            raw = _memory_get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set(self, key: str, value: Dict[str, Any], ttl: int = REDIS_TTL_SEC) -> None:
        payload = json.dumps(value, default=str)
        client = _get_redis()
        if client:
            try:
                client.setex(key, ttl, payload)
                return
            except Exception as exc:
                logger.warning("Redis set failed: %s", exc)
        _memory_set(key, payload, ttl)

    def delete(self, key: str) -> None:
        client = _get_redis()
        if client:
            try:
                client.delete(key)
            except Exception:
                pass
        with _MEMORY_LOCK:
            _MEMORY.pop(key, None)


_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def cache_key(media_type: str, file_hash: str, suffix: str = "") -> str:
    from backend.utils.performance_config import CACHE_VERSION
    base = f"aiforge:{CACHE_VERSION}:{media_type}:{file_hash}"
    return f"{base}:{suffix}" if suffix else base
