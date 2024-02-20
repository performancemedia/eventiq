from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from eventiq.middleware import Middleware
from eventiq.utils import to_async

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer, Service


class ErrorHandlerMiddleware(Middleware):
    def __init__(self, errors: type[Exception] | tuple[type[Exception]], callback):
        if not asyncio.iscoroutinefunction(callback):
            callback = to_async(callback)
        self.callback = callback
        self.exc = errors

    async def after_process_message(
        self,
        broker: Broker,
        service: Service,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ):
        if exc and isinstance(exc, self.exc):
            await self.callback(message, exc)
