from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from eventiq.middleware import Middleware

if TYPE_CHECKING:
    from eventiq.broker import Broker


class HealthCheckMiddleware(Middleware):
    """Middleware for performing basic health checks on broker"""

    BASE_DIR = os.getenv("HEALTHCHECK_DIR", "/tmp")  # nosec

    def __init__(self, interval: int = 30, file_mode: bool = False):
        self.interval = interval
        self.file_mode = file_mode
        self._broker: Broker | None = None
        self._task: asyncio.Task | None = None

    async def after_broker_connect(self, broker: Broker):
        self._broker = broker
        if self.file_mode:
            self._task = asyncio.create_task(self._run_forever())

    async def before_broker_disconnect(self, broker: Broker):
        if self.file_mode and self._task:
            self._task.cancel()
            await self._task

    async def _run_forever(self):
        p = Path(os.path.join(self.BASE_DIR, "healthy"))
        p.touch(exist_ok=True)
        while True:
            try:
                unhealthy = not self._broker.is_connected
            except Exception as e:
                self.logger.exception("Healthcheck failed", exc_info=e)
                unhealthy = True

            if unhealthy:
                p.rename(os.path.join(self.BASE_DIR, "unhealthy"))
                break
            await asyncio.sleep(self.interval)

    def get_health_status(self) -> bool:
        if self._broker:
            return self._broker.is_connected
        return False
