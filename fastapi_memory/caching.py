"""
Thin convenience layer around fastapi-cache2.

Re-exports the pieces you already use directly (``FmCacheManager``,
``FmMemoryBackend``, ``memorize``) and adds two small helpers:

- :func:`init_cache` - one-line setup for an in-memory or Redis-backed cache
- :func:`clear_cache` - ``await FmCacheManager.clear()``

The Redis backend is optional. Install it with::

    pip install "fastapi-memory[redis]"

If ``redis`` isn't installed, ``FmRedisBackend`` is simply ``None`` and
``init_cache(backend="redis", ...)`` raises a clear ``RuntimeError``
explaining how to fix it. The default ``backend="memory"`` works with no
extra dependencies, exactly like the original::

    FmCacheManager.init(FmMemoryBackend(), prefix="app-cache")
"""

from __future__ import annotations

from typing import Optional

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

# Aliases under fastapi-memory namespace
FmCacheManager = FastAPICache
FmMemoryBackend = InMemoryBackend
memorize = cache

try:  # pragma: no cover - exercised only when the `redis` extra is installed
    from fastapi_cache.backends.redis import RedisBackend
    from redis.asyncio import from_url as _redis_from_url

    FmRedisBackend = RedisBackend
    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover - redis extra not installed
    FmRedisBackend = None  # type: ignore[assignment, misc]
    _redis_from_url = None
    _REDIS_AVAILABLE = False


def init_cache(
    backend: str = "memory",
    *,
    prefix: str = "fastapi-cache",
    redis_url: Optional[str] = None,
) -> None:
    """
    Initialise :class:`FmCacheManager` with either an in-memory backend
    (default) or a Redis backend.

    Call this once during application startup, typically inside a
    ``lifespan`` handler::

        from contextlib import asynccontextmanager
        from fastapi import FastAPI
        from fastapi_memory import init_cache

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            init_cache(prefix="app-cache")  # in-memory (default)
            yield

        app = FastAPI(lifespan=lifespan)

    For Redis, pass ``backend="redis"`` and a connection URL::

        init_cache(backend="redis", prefix="app-cache", redis_url="redis://localhost:6379")

    Parameters
    ----------
    backend:
        ``"memory"`` (default) or ``"redis"``.
    prefix:
        Cache-key prefix, passed straight through to ``FmCacheManager.init``.
    redis_url:
        Connection string for Redis, e.g. ``redis://localhost:6379``.
        Required when ``backend="redis"``.
    """
    if backend == "memory":
        FmCacheManager.init(FmMemoryBackend(), prefix=prefix)
        return

    if backend == "redis":
        if not _REDIS_AVAILABLE:
            raise RuntimeError(
                "Redis backend requested but the 'redis' package is not "
                "installed. Install it with: pip install fastapi-memory[redis]"
            )
        if not redis_url:
            raise ValueError("redis_url is required when backend='redis'")

        client = _redis_from_url(redis_url, encoding="utf8", decode_responses=False)
        FmCacheManager.init(FmRedisBackend(client), prefix=prefix)
        return

    raise ValueError(f"Unknown backend {backend!r}, expected 'memory' or 'redis'")


async def clear_cache() -> None:
    """Clear the entire cache - thin wrapper around ``await FmCacheManager.clear()``."""
    await FmCacheManager.clear()


__all__ = [
    "FmCacheManager",
    "FmMemoryBackend",
    "FmRedisBackend",
    "memorize",
    "init_cache",
    "clear_cache",
]