from __future__ import annotations

import asyncio
import functools
from typing import Any, Awaitable, Callable

CF = Callable[..., Awaitable[Any]]


def run_async(func: Callable[..., Any]) -> CF:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

    return wrapper


def retry_async(max_retries: int = 5, backoff: int = 2):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            exc = None
            for i in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    exc = e
                    await asyncio.sleep(i**backoff)
            else:
                raise exc

        return wrapped

    return wrapper
