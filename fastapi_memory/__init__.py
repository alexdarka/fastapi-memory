"""
fastapi-memory
==============

Caching, retry, and resilient-HTTP helpers for FastAPI services.

This package provides response caching, retry policies, a resilient async
HTTP client, and cached config singletons — all in one import, designed for
FastAPI services that talk to slower upstream APIs.

Import from this package instead of juggling multiple dependencies directly::

    from fastapi_memory import (
        FmCacheManager, FmMemoryBackend, memorize,
        retry, stop_after_retries, exponential_backoff, retry_on_error,
        fm_lru,
    )

Higher-level helpers
---------------------
On top of the re-exports, fastapi-memory adds a few small conveniences:

- ``FmCacheManager``             -> wrapper with ``.init()`` / ``.get()`` / ``.set()`` / ``.clear()``
- ``default_retry()``            -> the "3 attempts, exponential backoff, skip 4xx" policy
- ``is_retryable_httpx_error``   -> the retry predicate behind ``default_retry``
- ``cached_singleton``           -> ``@fm_lru(maxsize=1)`` for settings-style singletons
- ``FmResilientClient``           -> persistent ``httpx.AsyncClient`` + retries + JSON helpers

See the README for full usage examples and a migration guide.
"""

from .caching import (
    FmCacheManager,
    FmMemoryBackend,
    FmRedisBackend,
    memorize,
)
from .config import cached_singleton, fm_lru
from .http import FmResilientClient
from .resilience import (
    default_retry,
    is_retryable_httpx_error,
    retry,
    retry_on_error,
    stop_after_retries,
    exponential_backoff,
)

__version__ = "0.1.1"

__all__ = [
    # caching
    "FmCacheManager",
    "FmMemoryBackend",
    "FmRedisBackend",
    "memorize",
    # resilience
    "retry",
    "stop_after_retries",
    "exponential_backoff",
    "retry_on_error",
    "default_retry",
    "is_retryable_httpx_error",
    # config
    "fm_lru",
    "cached_singleton",
    # http
    "FmResilientClient",
]
