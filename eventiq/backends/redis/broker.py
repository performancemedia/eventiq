from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict, TypeVar
from urllib.parse import urlparse

from redis.asyncio import Redis

from eventiq.broker import Broker

from ...exceptions import BrokerError
from ...settings import UrlBrokerSettings
from ...utils import get_safe_url

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Encoder, ServerInfo, Service


class RMessage(TypedDict):
    type: bytes | str
    pattern: bytes | str | None
    channel: bytes | str | None
    data: bytes


RedisRawMessage = TypeVar("RedisRawMessage", bound=RMessage)


class RedisBroker(Broker[RedisRawMessage, None]):
    """
    Broker implementation based on redis PUB/SUB and aioredis package
    :param url: connection string to redis
    :param connect_options: additional connection options passed to aioredis.from_url
    :param kwargs: base class arguments
    """

    WILDCARD_ONE = "*"
    WILDCARD_MANY = "*"
    Settings = UrlBrokerSettings

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

    @property
    def safe_url(self) -> str:
        return get_safe_url(self.url)

    def get_info(self) -> ServerInfo:
        parsed = urlparse(self.url)
        return {
            "host": parsed.hostname,
            "protocol": parsed.scheme,
            "pathname": parsed.path,
        }

    def parse_incoming_message(self, message: RedisRawMessage, encoder: Encoder) -> Any:
        return encoder.decode(message["data"])

    @property
    def is_connected(self) -> bool:
        return self.redis.connection.is_connected

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            raise BrokerError("Not connected")
        return self._redis

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        handler = self.get_handler(service, consumer)
        async with self.redis.pubsub() as sub:
            await sub.psubscribe(consumer.topic)
            while self._connected:
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
