# User Guide

This guide walks through the main usage patterns for `fastapi-memory`.

---

## 1. Caching

### In-memory cache (default)

The simplest setup — just call `init_cache()` once during startup:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_memory import init_cache, clear_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_cache(prefix="app-cache")  # in-memory by default
    yield

app = FastAPI(lifespan=lifespan)
```

### Redis cache

Install the Redis extra:

```bash
pip install "fastapi-memory[redis]"
```

Then pass `backend="redis"`:

```python
init_cache(
    backend="redis",
    prefix="app-cache",
    redis_url="redis://localhost:6379",
)
```

### Caching endpoint responses

Use the `@memorize` decorator to cache responses:

```python
from fastapi_memory import memorize

@memorize(expire=60)
async def get_data():
    ...
```

### Clearing the cache

```python
from fastapi_memory import clear_cache

@app.post("/api/cache/invalidate")
async def invalidate_cache():
    await clear_cache()
    return {"ok": True}
```

---

## 2. Retry — exponential backoff

### Using `default_retry()`

The default policy: 3 attempts, exponential backoff 2s→10s, retry network errors and 5xx, skip 4xx:

```python
from fastapi_memory import default_retry

@default_retry()
async def call_upstream():
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()
```

### Customizing retry parameters

```python
@default_retry(attempts=5, wait_max=30)
async def flaky_call():
    ...
```

### Using the raw building blocks

When you need full control over retry behavior:

```python
from fastapi_memory import retry, stop_after_retries, exponential_backoff, retry_on_error
import httpx

def my_predicate(exc):
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False

@retry(
    stop=stop_after_retries(5),
    wait=exponential_backoff(multiplier=2, min=2, max=30),
    retry=retry_on_error(my_predicate),
    reraise=True,
)
async def call_upstream():
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()
```

---

## 3. Config — cached singleton

Instead of the verbose `@lru_cache(maxsize=1)` pattern:

```python
from fastapi_memory import cached_singleton

class Settings:
    BASE_URL: str = "http://api.example.com:8080"
    CACHE_TTL: int = 300

@cached_singleton
def get_settings() -> Settings:
    return Settings()

config = get_settings()  # built once, reused on every call
```

`fm_lru` is also available if you need general LRU caching with a different maxsize:

```python
from fastapi_memory import fm_lru

@fm_lru(maxsize=128)
def get_config():
    return Settings()
```

---

## 4. Resilient HTTP client

`FmResilientClient` bundles a persistent `httpx.AsyncClient` with connection pooling,
automatic retries, and JSON response helpers.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_memory import FmResilientClient, init_cache

upstream = FmResilientClient(
    base_url="http://api.example.com:8080",
    timeout=30.0,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await upstream.start()
    init_cache(prefix="app-cache")
    yield
    await upstream.aclose()

app = FastAPI(lifespan=lifespan)

@app.get("/api/data")
async def get_data():
    return await upstream.get_json("data")
```

### `get_json` vs `get_raw`

- `get_json(path, params)` — converts HTTP errors to FastAPI `HTTPException` (502 for network errors, upstream status code for HTTP errors)
- `get_raw(path, params)` — raises the underlying exception directly

### Using as a context manager

```python
async with FmResilientClient(base_url="http://api.example.com") as client:
    data = await client.get_json("data")
```

### Customizing retry behavior

```python
upstream = FmResilientClient(
    base_url="http://api.example.com:8080",
    retry_attempts=5,        # retry up to 5 times
    retry_wait_min=1,        # start backoff at 1s
    retry_wait_max=30,       # max backoff 30s
)
```

---

## 5. Putting it all together

A typical FastAPI application using `fastapi-memory`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_memory import (
    FmResilientClient,
    init_cache,
    clear_cache,
    memorize,
    default_retry,
    cached_singleton,
)

class Settings:
    BASE_URL: str = "http://api.example.com:8080"
    CACHE_TTL: int = 300

@cached_singleton
def get_settings() -> Settings:
    return Settings()

upstream = FmResilientClient(
    base_url=get_settings().BASE_URL,
    timeout=30.0,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_cache(prefix="app-cache")
    await upstream.start()
    yield
    await upstream.aclose()

app = FastAPI(lifespan=lifespan)

@memorize(expire=60)
@default_retry()
@app.get("/api/data")
async def get_data():
    return await upstream.get_json("data")

@app.post("/api/cache/invalidate")
async def invalidate_cache():
    await clear_cache()
    return {"ok": True}