from __future__ import annotations

import asyncio
import functools
import socket
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

import anyio
from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R", bound=Any)


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def current_millis() -> int:
    return time.monotonic_ns() // 1000


def generate_instance_id() -> str:
    return socket.gethostname()


def to_async(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        return anyio.to_thread.run_sync(functools.partial(func, *args, **kwargs))

    return wrapper


def retry(max_retries: int = 5, backoff: int = 2):
    def _wrapper(
        func: Callable[P, R] | Callable[P, Awaitable[R]]
    ) -> Callable[P, R] | Callable[P, Awaitable[R]]:
        if asyncio.iscoroutinefunction(func):
            return _retry_async(func, max_retries, backoff)

        return _retry_sync(func, max_retries, backoff)

    return _wrapper


def _retry_async(
    func: Callable[P, Awaitable[R]] | Callable[P, R], max_retries: int, backoff: int
) -> Callable[P, R] | Callable[P, Awaitable[R]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        exc = None
        for i in range(1, max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                exc = e
                await asyncio.sleep(backoff**i)
        else:
            raise exc  # type: ignore

    return wrapper


def _retry_sync(func: Callable[P, R], max_retries: int, backoff: int) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        exc = None
        for i in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exc = e
                time.sleep(i**backoff)
        raise exc

    return wrapper
