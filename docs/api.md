# API Reference

This page documents every public export from `fastapi-memory`.

---

## Caching

### `FmCacheManager`

The main cache manager. Provides `.init()`, `.get()`, `.set()`, `.clear()`
methods for cache operations.

```python
from fastapi_memory import FmCacheManager, FmMemoryBackend
```

```python
# Initialise (call once during startup)
FmCacheManager.init(FmMemoryBackend(), prefix="app-cache")

# Get a cached value (returns None if not found)
cached = await FmCacheManager.get("loaderReport:SNF")

# Store a value in the cache
await FmCacheManager.set("my-key", {"data": "value"}, expire=60)

# Clear the entire cache
await FmCacheManager.clear()
```

**Methods:**

- `FmCacheManager.init(backend, prefix=..., expire=...)` — Initialise the cache backend.
- `FmCacheManager.get(key)` — Retrieve a cached value by key. Returns `None` if not found.
- `FmCacheManager.set(key, value, expire=...)` — Store a value. `expire` is TTL in seconds.
- `FmCacheManager.clear(namespace=..., key=...)` — Clear entire cache or a specific namespace/key.

---

### `FmMemoryBackend`

In-memory cache backend. Used as the default when calling `FmCacheManager.init()`.

```python
from fastapi_memory import FmMemoryBackend
```

---

### `FmRedisBackend`

Redis-backed cache backend. Available only when `redis` is installed.

Install Redis support:
```bash
pip install "fastapi-memory[redis]"
```

If `redis` is not installed, `FmRedisBackend` is `None`.

```python
from fastapi_memory import FmRedisBackend
if FmRedisBackend is not None:
    # Redis backend is available
    ...
```

---

### `memorize`

Decorator for caching endpoint/function responses.

Equivalent to the underlying `@cache(expire=...)` decorator.

```python
from fastapi_memory import memorize

@memorize(expire=60)
async def get_data():
    return {"data": "expensive computation"}
```

**Parameters:**
- `expire` *(int/float, optional)*: TTL in seconds. `None` means no expiry.

---

## Resilience

### `retry`

The underlying retry decorator (from tenacity). Use this when you need full control over retry behavior.

```python
from fastapi_memory import retry, stop_after_retries, exponential_backoff, retry_on_error

@retry(
    stop=stop_after_retries(3),
    wait=exponential_backoff(multiplier=1, min=2, max=10),
    retry=retry_on_error(my_predicate),
    reraise=True,
)
async def call_upstream():
    ...
```

---

### `stop_after_retries`

Controls how many times a retry is attempted.

```python
from fastapi_memory import stop_after_retries

# Stop after 5 attempts
stop = stop_after_retries(5)
```

---

### `exponential_backoff`

Controls the wait time between retries (exponential backoff).

```python
from fastapi_memory import exponential_backoff

# Wait 2s, 4s, 8s, 16s (up to 30s max)
wait = exponential_backoff(multiplier=2, min=2, max=30)
```

---

### `retry_on_error`

Retry predicate — decides whether to retry based on the exception.

```python
from fastapi_memory import retry_on_error
import httpx

# Retry on connection errors
pred = retry_on_error(lambda exc: isinstance(exc, httpx.ConnectError))
```

---

### `default_retry`

A ready-made decorator factory with a sensible default policy:

- **Attempts:** 3
- **Backoff:** exponential, 2s→10s
- **Retry:** network errors and 5xx responses; skip 4xx
- **Reraise:** on final failure

```python
from fastapi_memory import default_retry

@default_retry()
async def call_upstream():
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()
```

**Parameters:**
- `attempts` *(int)*: Max number of attempts (default: 3).
- `wait_min` *(float)*: Minimum wait in seconds (default: 2).
- `wait_max` *(float)*: Maximum wait in seconds (default: 10).
- `multiplier` *(float)*: Exponential multiplier (default: 1).
- `retry_on` *(callable, optional)*: Custom retry predicate.
- `reraise` *(bool)*: Whether to reraise on final failure (default: True).

```python
@default_retry(attempts=5, wait_max=30)
async def flaky_call():
    ...
```

---

### `is_retryable_httpx_error`

Default retry predicate for httpx calls:

- `httpx.RequestError` (timeout, connection errors, DNS failures) → **retry**
- `httpx.HTTPStatusError` with 5xx → **retry**
- `httpx.HTTPStatusError` with 4xx → **do NOT retry**
- Anything else → **do NOT retry**

```python
from fastapi_memory import is_retryable_httpx_error

is_retryable_httpx_error(httpx.ConnectError("boom"))  # True (network error)
is_retryable_httpx_error(...)  # True/False based on exception
```

---

## Config

### `fm_lru`

A re-export of `functools.lru_cache`. Use for general LRU caching.

```python
from fastapi_memory import fm_lru

@fm_lru(maxsize=128)
def get_config():
    return Settings()
```

---

### `cached_singleton`

Shorthand for `@fm_lru(maxsize=1)`. Turns a zero-argument factory function
into a cached singleton getter.

```python
from fastapi_memory import cached_singleton

@cached_singleton
def get_settings() -> Settings:
    return Settings()

config = get_settings()
```

---

## HTTP

### `FmResilientClient`

A persistent, retrying async HTTP client with connection pooling and
automatic retries.

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

**Parameters:**
- `base_url` *(str)*: Prepended to every `path` in requests.
- `timeout` *(float)*: Per-request timeout in seconds (default: 30).
- `verify` *(bool)*: TLS verification (default: True). Set to `False` for self-signed/internal endpoints.
- `max_connections` *(int)*: Max connections in pool (default: 20).
- `max_keepalive_connections` *(int)*: Max keepalive connections (default: 10).
- `retry_attempts` *(int)*: Retry count (default: 3).
- `retry_wait_min` *(float)*: Min wait for retries (default: 2).
- `retry_wait_max` *(float)*: Max wait for retries (default: 10).

**Methods:**
- `start()` — Start the client (call once on startup).
- `aclose()` — Close the client (call once on shutdown).
- `get_raw(path, params)` — GET with retries., returns parsed JSON or raw text.
- `get_json(path, params)` — Like `get_raw`, but converts errors to `httpx.HTTPException`.

**Context manager:**
```python
async with FmResilientClient(...) as client:
    ...