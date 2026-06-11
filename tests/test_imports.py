"""
Smoke tests:

- every name described in the README can be imported from `fastapi_memory`
- the small helpers (`cached_singleton`, `default_retry`, `init_cache` /
  `clear_cache`, `FmResilientClient`) behave as documented.

Run with:

    pip install -e ".[dev]"
    pytest
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

import fastapi_memory as fm


def test_top_level_reexports_exist():
    # fastapi-cache2
    assert fm.FmCacheManager is not None
    assert fm.FmMemoryBackend is not None
    assert fm.memorize is not None

    # tenacity
    assert fm.retry is not None
    assert fm.stop_after_retries is not None
    assert fm.exponential_backoff is not None
    assert fm.retry_on_error is not None

    # functools
    assert fm.fm_lru is not None

    # extra helpers
    assert fm.init_cache is not None
    assert fm.clear_cache is not None
    assert fm.default_retry is not None
    assert fm.is_retryable_httpx_error is not None
    assert fm.cached_singleton is not None
    assert fm.FmResilientClient is not None


def test_cached_singleton_returns_same_instance():
    calls = {"n": 0}

    @fm.cached_singleton
    def get_thing():
        calls["n"] += 1
        return object()

    a = get_thing()
    b = get_thing()

    assert a is b
    assert calls["n"] == 1


def test_is_retryable_httpx_error_policy():
    request = httpx.Request("GET", "http://example.test")

    # Network-level errors -> retry
    assert fm.is_retryable_httpx_error(httpx.ConnectError("boom", request=request))

    # 5xx -> retry
    resp_500 = httpx.Response(500, request=request)
    err_500 = httpx.HTTPStatusError("server error", request=request, response=resp_500)
    assert fm.is_retryable_httpx_error(err_500)

    # 4xx -> do not retry
    resp_404 = httpx.Response(404, request=request)
    err_404 = httpx.HTTPStatusError("not found", request=request, response=resp_404)
    assert not fm.is_retryable_httpx_error(err_404)

    # anything else -> do not retry
    assert not fm.is_retryable_httpx_error(ValueError("nope"))


def test_default_retry_retries_then_succeeds():
    attempts = {"n": 0}

    @fm.default_retry(attempts=3, wait_min=0, wait_max=0)
    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            request = httpx.Request("GET", "http://example.test")
            raise httpx.ConnectError("boom", request=request)
        return "ok"

    result = asyncio.run(flaky())

    assert result == "ok"
    assert attempts["n"] == 3


def test_default_retry_does_not_retry_4xx():
    attempts = {"n": 0}

    @fm.default_retry(attempts=3, wait_min=0, wait_max=0)
    async def bad_request():
        attempts["n"] += 1
        request = httpx.Request("GET", "http://example.test")
        response = httpx.Response(400, request=request)
        raise httpx.HTTPStatusError("bad request", request=request, response=response)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(bad_request())

    assert attempts["n"] == 1


def test_init_cache_memory_and_clear_cache():
    fm.init_cache(prefix="test-cache")
    asyncio.run(fm.clear_cache())


def test_resilient_client_get_json(monkeypatch):
    client = fm.FmResilientClient(base_url="http://example.test", retry_wait_min=0, retry_wait_max=0)

    async def fake_get(url, params=None):
        request = httpx.Request("GET", url)
        return httpx.Response(200, json={"ok": True}, request=request)

    async def run():
        await client.start()
        monkeypatch.setattr(client.client, "get", fake_get)
        result = await client.get_json("ping.jsp")
        await client.aclose()
        return result

    assert asyncio.run(run()) == {"ok": True}


def test_resilient_client_get_json_maps_4xx_to_http_exception(monkeypatch):
    from fastapi import HTTPException

    client = fm.FmResilientClient(base_url="http://example.test", retry_wait_min=0, retry_wait_max=0)

    async def fake_get(url, params=None):
        request = httpx.Request("GET", url)
        return httpx.Response(404, request=request)

    async def run():
        await client.start()
        monkeypatch.setattr(client.client, "get", fake_get)
        try:
            await client.get_json("missing.jsp")
        finally:
            await client.aclose()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(run())

    assert exc_info.value.status_code == 404