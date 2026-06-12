# fastapi-memory

**Caching, retry, and resilient-HTTP helpers for FastAPI services.**

fastapi-memory consolidates the most common patterns for FastAPI services
that talk to slower upstream APIs into one clean import:

- **Response caching** — in-memory or Redis, with `FmCacheManager.init()`
- **Retry policies** — exponential backoff, skip 4xx, with `default_retry()`
- **Cached singletons** — `@cached_singleton` for config objects
- **Resilient HTTP client** — persistent `httpx.AsyncClient` + retries + JSON helpers

## Installation

```bash
pip install fastapi-memory

# with optional Redis cache backend support
pip install "fastapi-memory[redis]"
```

## Quick import

Everything in fastapi-memory is accessible from one import:

```python
from fastapi_memory import (
    FmCacheManager, FmMemoryBackend, memorize,
    retry, stop_after_retries, exponential_backoff, retry_on_error,
    fm_lru,
    default_retry, is_retryable_httpx_error,
    cached_singleton,
    FmResilientClient,
)
```

---

## What's inside

| Module       | Provides                                                    | Helpers                                                     |
|--------------|-------------------------------------------------------------|-------------------------------------------------------------|
| `caching`    | `FmCacheManager`, `FmMemoryBackend`, `memorize`             | `FmRedisBackend`                                            |
| `resilience` | `retry`, `stop_after_retries`, `exponential_backoff`, etc.   | `default_retry()`, `is_retryable_httpx_error()`             |
| `config`     | `fm_lru`                                                    | `cached_singleton`                                          |
| `http`       | —                                                           | `FmResilientClient`                                         |

---

## Quick examples

### Caching

```python
from fastapi import FastAPI
from fastapi_memory import FmCacheManager, FmMemoryBackend, memorize

FmCacheManager.init(FmMemoryBackend(), prefix="app-cache")

@memorize(expire=60)
async def get_data():
    ...

# Manual get/set
await FmCacheManager.set("my-key", {"data": "value"}, expire=60)
cached = await FmCacheManager.get("my-key")

@app.post("/api/cache/invalidate")
async def invalidate_cache():
    await FmCacheManager.clear()
    return {"ok": True}
```

### Retry

```python
from fastapi_memory import default_retry

@default_retry()
async def call_upstream():
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()
```

### Cached singleton

```python
from fastapi_memory import cached_singleton

class Settings:
    BASE_URL: str = "http://api.example.com:8080"

@cached_singleton
def get_settings() -> Settings:
    return Settings()
```

### Resilient HTTP client

```python
from fastapi_memory import FmResilientClient

upstream = FmResilientClient(base_url="http://api.example.com:8080")
```

---

## Links

- [API Reference](api.md) — full reference for all exports
- [User Guide](guide.md) — migration examples and detailed usage
- [PyPI Package](https://pypi.org/project/fastapi-memory/)