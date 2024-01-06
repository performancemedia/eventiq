from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict, TypeVar

from redis.asyncio import Redis

from eventiq.broker import Broker

from .settings import RedisSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Service


class RMessage(TypedDict):
    type: bytes | str
    pattern: bytes | str | None
    channel: bytes | str | None
    data: bytes


RedisRawMessage = TypeVar("RedisRawMessage", bound=RMessage)


class RedisBroker(Broker[RedisRawMessage]):
    """
    Broker implementation based on redis PUB/SUB and aioredis package
    :param url: connection string to redis
    :param connect_options: additional connection options passed to aioredis.from_url
    :param kwargs: base class arguments
    """

    WILDCARD_ONE = "*"
    WILDCARD_MANY = "*"
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

    def parse_incoming_message(self, message: RedisRawMessage) -> Any:
        return self.encoder.decode(message["data"])

    @property
    def is_connected(self) -> bool:
        return self.redis.connection.is_connected

    @property
    def redis(self) -> Redis:
        assert self._redis is not None, "Not connected"
        return self._redis

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        handler = self.get_handler(service, consumer)
        async with self.redis.pubsub() as sub:
            await sub.psubscribe(consumer.topic)
            while self._running:
                message = await sub.get_message(ignore_subscribe_messages=True)
                if message:
                    await handler(message)

    async def _disconnect(self) -> None:
        await self.redis.aclose()

    async def _connect(self) -> None:
        self._redis = Redis.from_url(self.url, **self.connect_options)

    async def _publish(self, message: CloudEvent, **kwargs) -> None:
        data = self.encoder.encode(message)
        await self.redis.publish(message.topic, data)
