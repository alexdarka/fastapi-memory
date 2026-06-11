"""
Tiny helper built on top of ``functools.lru_cache`` for the
"build-it-once-and-reuse-it" settings/config pattern.

Re-exports ``lru_cache`` as ``fm_lru``, plus :func:`cached_singleton`, a
small shorthand for the common::

    @fm_lru(maxsize=1)
    def get_settings() -> Settings:
        return Settings()

pattern.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable, TypeVar

T = TypeVar("T")

# Alias under fastapi-memory namespace
fm_lru = lru_cache


def cached_singleton(func: Callable[[], T]) -> Callable[[], T]:
    """
    Shorthand for ``@fm_lru(maxsize=1)`` - turns a zero-argument factory
    function into a cached singleton getter.
    """
    return fm_lru(maxsize=1)(func)


__all__ = ["fm_lru", "cached_singleton"]