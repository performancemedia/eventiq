from __future__ import annotations

import os
from collections.abc import Awaitable
from pathlib import Path
from typing import Any, Callable

import anyio

from ..middleware import T
from .tasks import BackGroundTasksMiddleware


class HealthCheckMiddleware(BackGroundTasksMiddleware):
    """Middleware for performing basic health checks on broker"""

    BASE_DIR = os.getenv("HEALTHCHECK_DIR", "/tmp")  # nosec

    def __init__(
        self,
        interval: int = 30,
        predicates: list[Callable[..., Awaitable[Any]]] | None = None,
    ):
        super().__init__()
        self.interval = interval
        self.predicates = predicates

    async def after_broker_connect(self, broker: T):
        await super().after_broker_connect(broker)
        self.submit(self._run_forever, broker)

    async def _run_forever(self, broker: T) -> None:
        p = Path(os.path.join(self.BASE_DIR, "healthy"))
        p.touch(exist_ok=True)
        while True:
            try:
                unhealthy = not broker.is_connected

                if self.predicates:
                    with anyio.move_on_after(10) as scope:
                        async with anyio.create_task_group() as tg:
                            for f in self.predicates:
                                tg.start_soon(f)
                    if scope.cancel_called:
                        self.logger.warning("Healthcheck predicate timed out")
                        unhealthy = True
            except anyio.get_cancelled_exc_class():
                return
            except Exception as e:
                self.logger.exception("Healthcheck failed", exc_info=e)
                unhealthy = True

            if unhealthy:
                p.rename(os.path.join(self.BASE_DIR, "unhealthy"))
                break
            await anyio.sleep(self.interval)
