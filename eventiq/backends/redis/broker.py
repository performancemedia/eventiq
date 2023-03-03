from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aioredis

from eventiq.broker import Broker

from .settings import RedisSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, RawMessage, Service


class RedisBroker(Broker[dict[str, str]]):
    """
    Broker implementation based on redis PUB/SUB and aioredis package
    :param url: connection string to redis
    :param connect_options: additional connection options passed to aioredis.from_url
    :param kwargs: base class arguments
    """

    Settings = RedisSettings

    def __init__(
        self,
        *,
        url: str,
        connect_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:

        super().__init__(**kwargs)
        self.url = url
        self.connect_options = connect_options or {}
        self._redis = None

    def parse_incoming_message(self, message: RawMessage) -> Any:
        return message

    @property
    def is_connected(self) -> bool:
        return self.redis.connection.is_connected

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        handler = self.get_handler(service, consumer)
        psub = self.redis.pubsub()

        while True:
            message = await psub.get_message(ignore_subscribe_messages=True)
            if message:
                await handler(message)

    async def _disconnect(self) -> None:
        await self.redis.close()

    @property
    def redis(self) -> aioredis.Redis:
        assert self._redis is not None, "Not connected"
        return self._redis

    async def _connect(self) -> None:
        self._redis = aioredis.from_url(url=self.url, **self.connect_options)

    async def _publish(self, message: CloudEvent, **kwargs) -> None:
        data = self.encoder.encode(message)
        await self.redis.publish(message.topic, data)
