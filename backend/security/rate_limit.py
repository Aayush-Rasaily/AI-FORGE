"""
Redis-backed rate limiting — sliding window per IP or user.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

from backend.security.config import RATE_LIMIT_ENABLED

logger = logging.getLogger("ai_forge.security.rate_limit")


def _parse_limit(spec: str) -> Tuple[int, int]:
    """Parse '120/minute' → (120, 60)."""
    parts = spec.strip().split("/")
    count = int(parts[0])
    unit = (parts[1] if len(parts) > 1 else "minute").lower()
    window = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(unit, 60)
    return count, window


def check_rate_limit(
    key: str,
    limit_spec: str = "120/minute",
) -> Tuple[bool, int]:
    """
    Returns (allowed, retry_after_seconds).
    Falls open when Redis unavailable.
    """
    if not RATE_LIMIT_ENABLED:
        return True, 0

    max_count, window_sec = _parse_limit(limit_spec)
    redis_key = f"aiforge:ratelimit:{key}"

    try:
        from backend.utils.redis_cache import _get_redis
        client = _get_redis()
        if not client:
            return True, 0

        now = int(time.time())
        pipe = client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window_sec)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_sec + 1)
        _, _, count, _ = pipe.execute()

        if count > max_count:
            return False, window_sec
        return True, 0
    except Exception as exc:
        logger.debug("Rate limit check failed (allowing): %s", exc)
        return True, 0


def rate_limit_key(request, user_id: Optional[str] = None) -> str:
    if user_id:
        return f"user:{user_id}"
    client = getattr(request, "client", None)
    ip = client.host if client else "unknown"
    return f"ip:{ip}"
