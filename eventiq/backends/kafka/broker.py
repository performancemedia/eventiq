from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiokafka

from eventiq.broker import Broker
from eventiq.exceptions import BrokerError

from .settings import KafkaSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Service


class KafkaBroker(Broker[aiokafka.ConsumerRecord]):
    """
    Kafka backend
    :param bootstrap_servers: url or list of kafka servers
    :param publisher_options: extra options for AIOKafkaProducer
    :param consumer_options: extra options (defaults) for AIOKafkaConsumer
    :param kwargs: Broker base class parameters
    """

    Settings = KafkaSettings
    protocol = "kafka"

    def __init__(
        self,
        *,
        bootstrap_servers: str | list[str],
        publisher_options: dict[str, Any] | None = None,
        consumer_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:

        super().__init__(**kwargs)
        self.bootstrap_servers = bootstrap_servers
        self._publisher_options = publisher_options or {}
        self._consumer_options = consumer_options or {}
        self._publisher = None

    def parse_incoming_message(self, message: aiokafka.ConsumerRecord) -> Any:
        return self.encoder.decode(message.value)

    @property
    def is_connected(self) -> bool:
        return True

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        handler = self.get_handler(service, consumer)
        subscriber = aiokafka.AIOKafkaConsumer(
            consumer.topic,
            group_id=f"{service.name}:{consumer.name}",
            bootstrap_servers=self.bootstrap_servers,
            enable_auto_commit=False,
            **consumer.options.get("kafka_consumer_options", self._consumer_options),
        )
        await subscriber.start()
        while self._stopped:
            result = await subscriber.getmany(
                timeout_ms=consumer.options.get("timeout_ms", 600)
            )
            for tp, messages in result.items():

                if messages:
                    tasks: list[asyncio.Task] = [
                        asyncio.create_task(handler(message)) for message in messages  # type: ignore
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await subscriber.commit({tp: messages[-1].offset + 1})

    async def _disconnect(self):
        if self._publisher:
            await self._publisher.stop()

    @property
    def publisher(self) -> aiokafka.AIOKafkaProducer:
        if self._publisher is None:
            raise BrokerError("Broker not connected")
        return self._publisher

    async def _connect(self):
        self._publisher = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers, **self._publisher_options
        )
        await self._publisher.start()

    async def _publish(
        self,
        message: CloudEvent,
        key: Any | None = None,
        partition: Any | None = None,
        headers: dict[str, str] | None = None,
        timestamp_ms: int | None = None,
        **kwargs: Any,
    ):
        data = self.encoder.encode(message.dict())
        timestamp_ms = timestamp_ms or int(message.time.timestamp() * 1000)
        key = key or getattr(message, "key", message.id)
        headers = headers or {}
        headers.setdefault("Content-Type", self.encoder.CONTENT_TYPE)
        await self.publisher.send(
            topic=message.topic,
            value=data,
            key=key,
            partition=partition,
            headers=headers,
            timestamp_ms=timestamp_ms,
        )
