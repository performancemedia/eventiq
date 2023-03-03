import asyncio
import functools
import time

from eventiq.middleware import Middleware


def _logged_coro(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        self.logger.debug(f"Running func {func.__name__} with {args}, {kwargs}")
        start = time.perf_counter()
        try:
            return await func(self, *args, **kwargs)
        finally:
            delta = time.perf_counter() - start
            self.logger.debug("Completed after %.02fms.", delta * 1000)

    return wrapper


class DebugMeta(type):
    def __new__(mcs, name, bases, namespace):
        for k, v in namespace.items():
            if asyncio.iscoroutinefunction(v):
                namespace[k] = _logged_coro(v)
        return type.__new__(mcs, name, bases, namespace)


class DebugMiddleware(Middleware, metaclass=DebugMeta):
    """Log every event"""
