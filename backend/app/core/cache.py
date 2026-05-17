"""
Cache Helper — High-level wrapper over Redis.

Pattern: Get-or-fetch with TTL.
Use case: External API calls that don't need real-time freshness.

Examples:
    # 24-saat cache (gün boyu sabit veriler)
    @cached_async(key="kwh_price_try", ttl_seconds=86400)
    async def fetch_kwh_price() -> float:
        # Expensive Grounding call
        ...

    # Manual cache
    cached_value = await cache_get("kwh_price_try")
    if cached_value is None:
        value = await expensive_fetch()
        await cache_set("kwh_price_try", value, ttl_seconds=86400)

DESIGN:
- Graceful degradation: Redis down → return None, log warning
- JSON serialization (str, int, float, dict, list)
- ISO datetime tracking (when cached)
- TTL enforcement
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.core.redis_client import get_redis_client

logger = get_logger(__name__)


# ============================================================
# Cache Constants
# ============================================================
CACHE_PREFIX = "optiwallet:cache:"


# ============================================================
# Cache Get
# ============================================================
async def cache_get(key: str) -> dict | None:
    """
    Cache'ten değer al.

    Returns:
        Dict ile {value, cached_at} veya None (cache miss / Redis down).
    """
    full_key = f"{CACHE_PREFIX}{key}"

    try:
        client = get_redis_client()
        raw = await client.get(full_key)

        if raw is None:
            logger.debug("cache_miss", key=key)
            return None

        data = json.loads(raw)
        logger.debug("cache_hit", key=key, cached_at=data.get("cached_at"))
        return data

    except Exception as exc:
        # Redis down / network error → graceful degradation
        logger.warning(
            "cache_get_failed",
            key=key,
            error=str(exc)[:200],
        )
        return None


# ============================================================
# Cache Set
# ============================================================
async def cache_set(
    key: str,
    value: Any,
    ttl_seconds: int = 86400,
) -> bool:
    """
    Cache'e değer yaz.

    Args:
        key: Cache anahtarı.
        value: JSON-serializable değer (dict, list, str, int, float).
        ttl_seconds: Time-to-live (default 24 saat).

    Returns:
        True if successful, False otherwise.
    """
    full_key = f"{CACHE_PREFIX}{key}"

    try:
        # Wrapper with timestamp
        payload = {
            "value": value,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": ttl_seconds,
        }

        client = get_redis_client()
        await client.setex(
            full_key,
            ttl_seconds,
            json.dumps(payload, ensure_ascii=False),
        )

        logger.info(
            "cache_set",
            key=key,
            ttl_seconds=ttl_seconds,
            value_preview=str(value)[:100],
        )
        return True

    except Exception as exc:
        logger.warning(
            "cache_set_failed",
            key=key,
            error=str(exc)[:200],
        )
        return False


# ============================================================
# Cache Delete (manual invalidation)
# ============================================================
async def cache_delete(key: str) -> bool:
    """Cache'ten anahtarı sil."""
    full_key = f"{CACHE_PREFIX}{key}"

    try:
        client = get_redis_client()
        result = await client.delete(full_key)
        logger.info("cache_delete", key=key, existed=bool(result))
        return bool(result)
    except Exception as exc:
        logger.warning("cache_delete_failed", key=key, error=str(exc))
        return False


# ============================================================
# Get-or-Fetch Pattern (high-level)
# ============================================================
async def get_or_fetch(
    key: str,
    fetch_func: Any,
    ttl_seconds: int = 86400,
) -> tuple[Any, str]:
    """
    Cache'ten al, yoksa fetch et ve cache'e koy.

    Args:
        key: Cache anahtarı.
        fetch_func: Async callable (cache miss durumunda çağrılır).
        ttl_seconds: TTL.

    Returns:
        Tuple (value, source) — source "cache" veya "grounding"

    Example:
        async def fetch_price():
            # Expensive Gemini Grounding call
            return 2.85

        price, source = await get_or_fetch(
            "kwh_price",
            fetch_price,
            ttl_seconds=86400,
        )
        # source = "cache" or "grounding"
    """
    # Try cache first
    cached = await cache_get(key)
    if cached is not None:
        return cached["value"], "cache"

    # Cache miss → fetch
    logger.info("cache_miss_fetching", key=key)
    try:
        fresh_value = await fetch_func()

        # Cache'e koy (fire-and-forget mantığı ama await ediyoruz hata için)
        await cache_set(key, fresh_value, ttl_seconds=ttl_seconds)

        return fresh_value, "grounding"

    except Exception as exc:
        logger.error(
            "get_or_fetch_failed",
            key=key,
            error=str(exc)[:200],
        )
        raise