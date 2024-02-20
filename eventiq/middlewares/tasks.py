from __future__ import annotations

import functools
from datetime import timedelta
from typing import TYPE_CHECKING

import anyio

from eventiq.middleware import Middleware, T

if TYPE_CHECKING:
    from anyio._core._tasks import TaskGroup


class BackGroundTasksMiddleware(Middleware):
    def __init__(self) -> None:
        self._tg: TaskGroup | None = None

    @property
    def tg(self) -> TaskGroup:
        if self._tg is None:
            raise ValueError("Task group not started")
        return self._tg

    async def before_broker_connect(self, broker: T) -> None:
        self._tg = anyio.create_task_group()
        await self._tg.__aenter__()

    async def after_broker_disconnect(self, broker: T) -> None:
        self.tg.cancel_scope.cancel()
        await self.tg.__aexit__(None, None, None)
        self._tg = None

    def submit(self, fn, *args, **kwargs) -> None:
        if kwargs:
            fn = functools.partial(fn, **kwargs)
        self.tg.start_soon(fn, *args)

    def cancel(self) -> None:
        self.tg.cancel_scope.cancel()

    def submit_periodic(self, fn, interval: float | timedelta, *args, **kwargs) -> None:
        if isinstance(interval, timedelta):
            interval = interval.total_seconds()

        async def _wrapper():
            while True:
                await anyio.sleep(interval)
                await fn(*args, **kwargs)

        self.submit(_wrapper)
