"""
A small resilient async HTTP client: a persistent ``httpx.AsyncClient`` with
connection-pooling defaults plus automatic retries via
:func:`fastapi_memory.resilience.default_retry`.

This mirrors the ``_upstream_get_raw`` / ``_upstream_get`` pattern: a single
shared client, retried with exponential backoff on network errors and 5xx
responses, with a thin layer that turns final failures into FastAPI
``HTTPException``s.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import HTTPException

from .resilience import default_retry


class FmResilientClient:
    """
    A persistent, retrying async HTTP client for talking to an upstream API.

    Example
    -------
        from contextlib import asynccontextmanager
        from fastapi import FastAPI
        from fastapi_memory import FmResilientClient

        upstream = FmResilientClient(
            base_url="http://api.example.com:8080",
            timeout=30.0,
        )

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await upstream.start()
            yield
            await upstream.aclose()

        app = FastAPI(lifespan=lifespan)

        @app.get("/api/data")
        async def get_data():
            return await upstream.get_json("data")

    Parameters
    ----------
    base_url:
        Prepended to every ``path`` passed to :meth:`get_raw` / :meth:`get_json`.
        Leave empty to pass full URLs directly.
    timeout:
        Per-request timeout in seconds, forwarded to ``httpx.AsyncClient``.
    verify:
        TLS verification, forwarded to ``httpx.AsyncClient``. Set to
        ``False`` for self-signed/internal endpoints (matches
        ``httpx.AsyncClient(verify=False)`` in the original code).
    max_connections / max_keepalive_connections:
        Forwarded to ``httpx.Limits``.
    retry_attempts / retry_wait_min / retry_wait_max:
        Forwarded to :func:`default_retry` for every request made through
        this client.
    """

    def __init__(
        self,
        base_url: str = "",
        *,
        timeout: float = 30.0,
        verify: bool = True,
        max_connections: int = 20,
        max_keepalive_connections: int = 10,
        retry_attempts: int = 3,
        retry_wait_min: float = 2,
        retry_wait_max: float = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify = verify
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
        )
        self._retry_attempts = retry_attempts
        self._retry_wait_min = retry_wait_min
        self._retry_wait_max = retry_wait_max
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Create the underlying ``httpx.AsyncClient``. Call once on startup."""
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            verify=self._verify,
            limits=self._limits,
        )

    async def aclose(self) -> None:
        """Close the underlying client. Call once on shutdown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "FmResilientClient":
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        """The underlying ``httpx.AsyncClient``. Raises if not started yet."""
        if self._client is None:
            raise RuntimeError(
                "FmResilientClient is not started - call `await client.start()` "
                "during application startup (e.g. in your lifespan handler), "
                "or use it as `async with FmResilientClient(...) as client:`."
            )
        return self._client

    def _url(self, path: str) -> str:
        if self.base_url and not path.startswith(("http://", "https://")):
            return f"{self.base_url}/{path.lstrip('/')}"
        return path

    async def get_raw(self, path: str, params: Optional[dict] = None) -> Any:
        """
        ``GET path`` with retries (see :func:`default_retry`).

        Returns the parsed JSON body if possible, otherwise the raw response
        text. Raises the underlying ``httpx`` exception on final failure -
        use :meth:`get_json` if you'd rather get a FastAPI ``HTTPException``.
        """

        @default_retry(
            attempts=self._retry_attempts,
            wait_min=self._retry_wait_min,
            wait_max=self._retry_wait_max,
        )
        async def _do_request() -> Any:
            resp = await self.client.get(self._url(path), params=params)
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError:
                return resp.text or ""

        return await _do_request()

    async def get_json(self, path: str, params: Optional[dict] = None) -> Any:
        """
        Like :meth:`get_raw`, but converts ``httpx`` errors (after retries
        are exhausted) into FastAPI ``HTTPException``s:

        - ``httpx.HTTPStatusError`` -> ``HTTPException(status_code=<upstream status>)``
        - ``httpx.RequestError``    -> ``HTTPException(status_code=502)``
        """
        try:
            return await self.get_raw(path, params)
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail="Upstream request failed"
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="Upstream request error") from exc


__all__ = ["FmResilientClient"]