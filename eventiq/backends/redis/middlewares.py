from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aioredis import Redis

from eventiq import Middleware

from ...utils.functools import retry_async

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer
    from eventiq.types import Encoder

    from .broker import RedisBroker


class RedisResultMiddleware(Middleware):
    def __init__(self, bucket: str, encoder: Encoder | None = None, ttl: int = 3600):
        self.bucket = bucket
        if encoder is None:
            from eventiq.encoders import get_default_encoder

            encoder = get_default_encoder()
        self.encoder = encoder
        self.ttl = ttl
        self._redis: Redis | None = None

    @property
    def redis(self) -> Redis:
        assert self._redis
        return self._redis

    async def after_broker_connect(self, broker: RedisBroker) -> None:  # type: ignore[override]
        assert isinstance(broker, RedisBroker)
        self._redis = broker.redis

    @retry_async(max_retries=3, backoff=10)
    async def after_process_message(
        self,
        broker: Broker,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ) -> None:
        if exc is None and consumer.options.get("store_results"):
            data = self.encoder.encode(result)
            ttl = consumer.options.get("result_ttl", self.ttl)
            await self.redis.set(f"{consumer.name}:{message.id}", data, ex=ttl)

    @retry_async(max_retries=3, backoff=5)
    async def get_message_result(self, consumer_name: str, message_id: str):
        value = await self.redis.get(f"{consumer_name}:{message_id}")
        return self.encoder.decode(value)
