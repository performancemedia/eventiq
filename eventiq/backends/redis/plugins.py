from __future__ import annotations

from typing import Any

from eventiq import CloudEvent, Consumer, Middleware, Service
from eventiq.plugins import BrokerPlugin
from eventiq.types import ID, ResultBackend

from .broker import RedisBroker


class _RedisResultMiddleware(Middleware[RedisBroker]):
    def __init__(self, store_exceptions: bool, ttl: int):
        self.store_exceptions = store_exceptions
        self.ttl = ttl

    async def after_process_message(
        self,
        broker: RedisBroker,
        service: Service,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ) -> None:
        if not consumer.store_results:
            return

        if exc is None:
            data = broker.encoder.encode(result)

        elif exc and self.store_exceptions:
            data = broker.encoder.encode(
                {"type": type(exc).__name__, "detail": str(exc)}
            )
        else:
            return
        await broker.redis.set(f"{service.name}:{message.id}", data, ex=self.ttl)


class RedisResultBackend(BrokerPlugin[RedisBroker], ResultBackend):
    def __init__(
        self, broker: RedisBroker, store_exceptions: bool = False, ttl: int = 3600
    ):
        super().__init__(broker)
        broker.add_middleware(_RedisResultMiddleware(store_exceptions, ttl))

    async def get_result(self, service: str, message_id: ID):
        res = await self.broker.redis.get(f"{service}:{message_id}")
        if res:
            return self.broker.encoder.decode(res)
