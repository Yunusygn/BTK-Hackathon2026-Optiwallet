"""
Redis Client — Async Singleton.

Pattern: Single shared connection pool (redis-py async).
Used by:
- Cache helpers (cache.py)
- Future: Session storage, rate limiting

Performance:
- Connection pool reuse (no new connection per request)
- Async operations (non-blocking)
- Graceful degradation if Redis down
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Singleton Connection
# ============================================================
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """
    Async Redis client singleton.

    İlk çağrıda oluşturur, sonra cache'ler.
    Connection pool'u otomatik yönetir.
    """
    global _redis_client

    if _redis_client is None:
        redis_url = getattr(settings, "REDIS_URL", "redis://redis:6379/0")

        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

        logger.info(
            "redis_client_initialized",
            url=redis_url.split("@")[-1] if "@" in redis_url else redis_url,
        )

    return _redis_client


async def close_redis_client() -> None:
    """Redis bağlantısını kapat (shutdown için)."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_client_closed")