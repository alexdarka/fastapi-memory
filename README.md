# fastapi-memory

Caching, retry, and resilient-HTTP helpers for FastAPI services.

A single package that provides response caching, retry policies, a resilient
async HTTP client, and cached config singletons — tailored for FastAPI
projects that talk to upstream APIs.

```python
from fastapi_memory import (
    FmCacheManager, FmMemoryBackend, memorize,
    retry, stop_after_retries, exponential_backoff, retry_on_error,
    fm_lru,
)
```

## Why

Most FastAPI services that proxy slower or less-reliable upstream APIs end up
re-writing the same patterns:

1. A **cache** for endpoints or data that don't change often.
2. A **retry policy** for upstream calls — retry network errors and 5xx, but not 4xx.
3. A **cached singleton** config object (build once, reuse everywhere).
4. A **resilient HTTP client** with connection pooling and retries baked in.

`fastapi-memory` consolidates all of these into one import, with ready-made
helpers so you don't have to re-derive common patterns every time.

## Installation

```bash
# From PyPI
pip install fastapi-memory

# With optional Redis cache backend support
pip install "fastapi-memory[redis]"
```

## What's inside

| Module       | Provides                                                          | Adds                                                      |
|--------------|-------------------------------------------------------------------|-----------------------------------------------------------|
| `caching`    | `FmCacheManager`, `FmMemoryBackend`, `memorize`, `FmRedisBackend` | `FmCacheManager.get()`, `.set()`, `.clear()`, `.init()`   |
| `resilience` | `retry`, `stop_after_retries`, `exponential_backoff`, `retry_on_error` | `default_retry()`, `is_retryable_httpx_error()`           |
| `config`     | `fm_lru`                                                          | `cached_singleton`                                        |
| `http`       | —                                                                 | `FmResilientClient`                                       |

Everything above is re-exported from the top-level `fastapi_memory` package,
so `from fastapi_memory import <anything in the table>` works.

---

## Quick start

### Caching — response caching with a single call

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_memory import FmCacheManager, FmMemoryBackend, memorize

@asynccontextmanager
async def lifespan(app: FastAPI):
    FmCacheManager.init(FmMemoryBackend(), prefix="app-cache")  # in-memory
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/api/data")
@memorize(expire=60)
async def get_data():
    return {"data": "computed result"}

# Manual get/set
await FmCacheManager.set("my-key", {"data": "value"}, expire=60)
cached = await FmCacheManager.get("my-key")

@app.post("/api/cache/invalidate")
async def invalidate_cache():
    await FmCacheManager.clear()
    return {"ok": True}
```

### Switching to Redis later

```python
from fastapi_memory import FmCacheManager, FmRedisBackend

FmCacheManager.init(
    FmRedisBackend(redis_client),
    prefix="app-cache",
)
```

### Retry — exponential backoff with sensible defaults

```python
from fastapi_memory import default_retry

@default_retry()
async def call_upstream():
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()
```

`default_retry()` retries up to 3 times with exponential backoff (2s–10s),
skip 4xx, reraise on final failure. Override any piece:

```python
@default_retry(attempts=5, wait_max=30)
async def flaky_call():
    ...
```

### Config — cached singleton

```python
from fastapi_memory import cached_singleton

class Settings:
    BASE_URL: str = "http://api.example.com:8080"
    CACHE_TTL: int = 300

@cached_singleton
def get_settings() -> Settings:
    return Settings()

config = get_settings()
```

### Resilient HTTP client

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_memory import FmResilientClient, FmCacheManager, FmMemoryBackend

upstream = FmResilientClient(
    base_url="http://api.example.com:8080",
    timeout=30.0,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await upstream.start()
    FmCacheManager.init(FmMemoryBackend(), prefix="app-cache")
    yield
    await upstream.aclose()

app = FastAPI(lifespan=lifespan)

@app.get("/api/data")
async def get_data():
    return await upstream.get_json("data")
```

`upstream.get_raw(path, params)` is also available if you want the raw
exceptions instead of `HTTPException`.

---

## Project layout

```
fastapi-memory/
├── pyproject.toml
├── setup.py
├── README.md
├── LICENSE
├── fastapi_memory/
│   ├── __init__.py          # re-exports everything
│   ├── caching.py            # FmCacheManager, FmMemoryBackend, memorize
│   ├── resilience.py         # retry + default_retry, is_retryable_httpx_error
│   ├── config.py             # fm_lru + cached_singleton
│   └── http.py               # FmResilientClient
└── tests/
    └── test_imports.py
```

## Updating `requirements.txt`

Replace:

```
tenacity>=8.3.0
fastapi-cache2>=0.2.2
redis>=5.0.0
```

with:

```
fastapi-memory @ file:///path/to/fastapi-memory
```

(or once published: `fastapi-memory>=0.1.0`, optionally `fastapi-memory[redis]`.)