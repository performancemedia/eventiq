from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aio_pika

from eventiq.broker import Broker

from .settings import RabbitMQSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Service


class RabbitmqBroker(Broker[aio_pika.abc.AbstractIncomingMessage]):
    """
    RabbitMQ broker implementation, based on `aio_pika` library.
    :param url: rabbitmq connection string
    :param default_prefetch_count: default number of messages to prefetch (per queue)
    :param queue_options: additional queue options
    :param exchange_name: global exchange name
    :param connection_options: additional connection options passed to aio_pika.connect_robust
    :param kwargs: Broker base class parameters
    """

    Settings = RabbitMQSettings

    def __init__(
        self,
        *,
        url: str,
        default_prefetch_count: int = 10,
        queue_options: dict[str, Any] | None = None,
        exchange_name: str = "events",
        connection_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:

        super().__init__(**kwargs)
        self.url = url
        self.default_prefetch_count = default_prefetch_count
        self.queue_options = queue_options or {}
        self.exchange_name = exchange_name
        self.connection_options = connection_options or {}
        self._connection = None
        self._exchange = None
        self._channels: list[aio_pika.abc.AbstractRobustChannel] = []

    @property
    def connection(self) -> aio_pika.RobustConnection:
        return self._connection

    @property
    def exchange(self) -> aio_pika.abc.AbstractRobustExchange:
        return self._exchange

    async def _connect(self) -> None:
        self._connection = await aio_pika.connect_robust(
            self.url, **self.connection_options
        )
        channel = await self.connection.channel()
        self._exchange = await channel.declare_exchange(
            name=self.exchange_name, type=aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def _disconnect(self) -> None:
        await asyncio.gather(
            *[c.close() for c in self._channels], return_exceptions=True
        )
        await self.connection.close()

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        """
        TODO: refactor rabbitmq to use 1 queue per service and internal handlers [routing_key:consumer_handler] dict
        to route the messages to consumers
        :param service:
        :param consumer:
        :return:
        """
        channel = await self.connection.channel()
        await channel.set_qos(
            prefetch_count=consumer.options.get(
                "prefetch_count", self.default_prefetch_count
            )
        )
        options: dict[str, Any] = consumer.options.get(
            "queue_options", self.queue_options
        )
        is_durable = not consumer.dynamic
        options.setdefault("durable", is_durable)
        queue_name = f"{service.name}:{consumer.name}"
        queue = await channel.declare_queue(name=queue_name, **options)
        await queue.bind(self._exchange, routing_key=consumer.topic)
        handler = self.get_handler(service, consumer)
        await queue.consume(handler)
        self._channels.append(channel)

    async def _publish(self, message: CloudEvent, **kwargs) -> None:
        body = self.encoder.encode(
            message.dict(
                exclude={
                    "id",
                    "type",
                    "source",
                    "content_type",
                    "version",
                    "time",
                    "topic",
                }
            )
        )
        headers = kwargs.pop("headers", {})
        headers.setdefault("specversion", message.specversion)
        headers.setdefault("Content-Type", self.encoder.CONTENT_TYPE)
        msg = aio_pika.Message(
            headers=headers,
            body=body,
            app_id=message.source,
            content_type=message.content_type,
            timestamp=message.time,
            message_id=str(message.id),
            type=message.type,
            content_encoding="UTF-8",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self.exchange.publish(msg, routing_key=message.topic, **kwargs)

    async def _ack(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        await message.ack()

    async def _nack(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        await message.reject(requeue=True)

    @property
    def is_connected(self) -> bool:
        return not self.connection.is_closed

    def parse_incoming_message(
        self, message: aio_pika.abc.AbstractIncomingMessage
    ) -> Any:
        msg = self.encoder.decode(message.body)
        if not isinstance(msg, dict):
            raise TypeError(f"Expected dict, got {type(msg)}")
        msg.update(
            {
                "id": message.message_id,
                "type": message.type,
                "source": message.app_id,
                "content_type": message.content_type,
                "version": message.headers.get("specversion"),
                "time": message.timestamp,
                "topic": message.routing_key,
            }
        )
        return msg
