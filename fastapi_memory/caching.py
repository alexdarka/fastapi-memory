"""
Thin convenience layer around fastapi-cache2.

Re-exports the pieces you already use directly (``FmMemoryBackend``,
``memorize``) and adds :class:`FmCacheManager`, a wrapper with
``.init()`` / ``.get()`` / ``.set()`` / ``.clear()`` methods.

The Redis backend is optional. Install it with::

    pip install "fastapi-memory[redis]"

If ``redis`` isn't installed, ``FmRedisBackend`` is simply ``None``.
The default ``backend="memory"`` works with no extra dependencies::

    FmCacheManager.init(FmMemoryBackend(), prefix="app-cache")
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

# Aliases under fastapi-memory namespace
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


class FmCacheManager:
    """
    Wrapper around FastAPICache providing ``.get()`` / ``.set()`` / ``.clear()``
    / ``.init()`` methods.

    Example::

        from fastapi_memory import FmCacheManager, FmMemoryBackend

        FmCacheManager.init(FmMemoryBackend(), prefix="app-cache")

        # manual get/set
        await FmCacheManager.set("my-key", {"data": "value"}, expire=60)
        cached = await FmCacheManager.get("my-key")

        # clear entire cache
        await FmCacheManager.clear()
    """

    @staticmethod
    def init(
        backend: Any,
        *,
        prefix: str = "fastapi-cache",
        expire: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialise the underlying cache backend."""
        FastAPICache.init(backend, prefix=prefix, expire=expire, **kwargs)

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """
        Retrieve a cached value by key.

        Returns ``None`` if the key is not found or has expired.
        The key is automatically prefixed with the prefix set during ``init()``.
        """
        backend = FastAPICache.get_backend()
        coder = FastAPICache.get_coder()
        prefix = FastAPICache.get_prefix()
        full_key = f"{prefix}:{key}"
        raw = await backend.get(full_key)
        if raw is None:
            return None
        return coder.decode(raw)

    @staticmethod
    async def set(
        key: str,
        value: Any,
        *,
        expire: Optional[int] = None,
    ) -> None:
        """
        Store a value in the cache.

        Parameters
        ----------
        key:
            Cache key (prefix is added automatically).
        value:
            The value to cache (must be serializable by the configured coder).
        expire:
            TTL in seconds. ``None`` uses the default expiry set during ``init()``.
        """
        backend = FastAPICache.get_backend()
        coder = FastAPICache.get_coder()
        prefix = FastAPICache.get_prefix()
        full_key = f"{prefix}:{key}"
        encoded = coder.encode(value)
        await backend.set(full_key, encoded, expire=expire)

    @staticmethod
    async def clear(
        namespace: Optional[str] = None,
        key: Optional[str] = None,
    ) -> int:
        """Clear the entire cache, or a specific namespace/key."""
        return await FastAPICache.clear(namespace=namespace, key=key)


__all__ = [
    "FmCacheManager",
    "FmMemoryBackend",
    "FmRedisBackend",
    "memorize",
]
