"""
Retry helpers built on top of tenacity.

Re-exports the building blocks you already use directly (``retry``,
``stop_after_retries``, ``exponential_backoff``, ``retry_on_error``) and
adds two small helpers for retry policies on flaky upstream services:

- :func:`is_retryable_httpx_error` - retry network errors and 5xx responses,
  but never 4xx client errors.
- :func:`default_retry` - a ready-made decorator factory for "retry up to 3
  times with exponential backoff (2s..10s), reraising on final failure".

These two together are exactly equivalent to::

    def _should_retry(exc):
        if isinstance(exc, httpx.RequestError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code >= 500
        return False

    @retry(
        stop=stop_after_retries(3),
        wait=exponential_backoff(multiplier=1, min=2, max=10),
        retry=retry_on_error(_should_retry),
        reraise=True,
    )
    async def call_upstream(...):
        ...
"""

from __future__ import annotations

from typing import Callable, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

# Aliases under fastapi-memory namespace
stop_after_retries = stop_after_attempt
exponential_backoff = wait_exponential
retry_on_error = retry_if_exception

RetryPredicate = Callable[[BaseException], bool]


def is_retryable_httpx_error(exc: BaseException) -> bool:
    """
    Default retry policy for httpx calls:

    - ``httpx.RequestError`` (timeouts, connection errors, DNS failures, ...) -> retry
    - ``httpx.HTTPStatusError`` with a 5xx response                           -> retry
    - ``httpx.HTTPStatusError`` with a 4xx response                           -> do NOT retry
    - anything else                                                            -> do NOT retry
    """
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def default_retry(
    attempts: int = 3,
    *,
    wait_min: float = 2,
    wait_max: float = 10,
    multiplier: float = 1,
    retry_on: Optional[RetryPredicate] = None,
    reraise: bool = True,
):
    """
    A pre-configured :func:`tenacity.retry` decorator factory.

    Calling ``default_retry()`` with no arguments is equivalent to::

        @retry(
            stop=stop_after_retries(3),
            wait=exponential_backoff(multiplier=1, min=2, max=10),
            retry=retry_on_error(is_retryable_httpx_error),
            reraise=True,
        )

    Example
    -------
        @default_retry()
        async def call_upstream():
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()

    Override any piece as needed, e.g. ``default_retry(attempts=5)`` or
    ``default_retry(retry_on=my_predicate)``.
    """
    condition = retry_on or is_retryable_httpx_error
    return retry(
        stop=stop_after_retries(attempts),
        wait=exponential_backoff(multiplier=multiplier, min=wait_min, max=wait_max),
        retry=retry_on_error(condition),
        reraise=reraise,
    )


__all__ = [
    "retry",
    "stop_after_retries",
    "exponential_backoff",
    "retry_on_error",
    "default_retry",
    "is_retryable_httpx_error",
]