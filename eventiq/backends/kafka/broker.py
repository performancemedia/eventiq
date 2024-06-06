from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import aiokafka
import anyio

from eventiq.broker import Broker
from eventiq.exceptions import BrokerError

from ...utils import get_safe_url, utc_now
from .settings import KafkaSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Encoder, ServerInfo, Service


class KafkaBroker(Broker[aiokafka.ConsumerRecord, None]):
    """
    Kafka backend
    :param bootstrap_servers: url or list of kafka servers
    :param publisher_options: extra options for AIOKafkaProducer
    :param consumer_options: extra options (defaults) for AIOKafkaConsumer
    :param kwargs: Broker base class parameters
    """

    WILDCARD_MANY = "*"
    WILDCARD_ONE = r"\w+"

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

    def parse_incoming_message(
        self, message: aiokafka.ConsumerRecord, encoder: Encoder
    ) -> Any:
        return encoder.decode(message.value)

    @property
    def is_connected(self) -> bool:
        return True

    def _should_nack(self, message: aiokafka.ConsumerRecord) -> bool:
        if (
            message.timestamp
            < (utc_now() + timedelta(seconds=self.validate_error_delay)).timestamp()
        ):
            return True
        return False

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        handler = self.get_handler(service, consumer)
        subscriber = aiokafka.AIOKafkaConsumer(
            group_id=f"{service.name}:{consumer.name}",
            bootstrap_servers=self.bootstrap_servers,
            enable_auto_commit=False,
            **consumer.options.get("kafka_consumer_options", self._consumer_options),
        )
        await subscriber.start()
        subscriber.subscribe(pattern=self.format_topic(consumer.topic))
        try:
            while self._connected:
                result = await subscriber.getmany(
                    timeout_ms=consumer.options.get("timeout_ms", 600)
                )

                for tp, messages in result.items():
                    if messages:
                        async with anyio.create_task_group() as tg:
                            for message in messages:
                                tg.start_soon(handler, message)
                        await subscriber.commit({tp: messages[-1].offset + 1})
        finally:
            if consumer.dynamic:
                subscriber.unsubscribe()

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
        data = self.encoder.encode(message.model_dump())
        timestamp_ms = timestamp_ms or int(message.time.timestamp() * 1000)
        key = key or getattr(message, "key", str(message.id))
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

    def get_info(self) -> ServerInfo:
        if isinstance(self.bootstrap_servers, str):
            parsed = urlparse(self.bootstrap_servers)
            return {
                "host": parsed.hostname,
                "protocol": parsed.scheme,
                "pathname": parsed.path,
            }
        return {
            "host": ",".join(
                urlparse(server).hostname or "" for server in self.bootstrap_servers
            ),
            "protocol": "kafka",
            "pathname": "",
        }

    @property
    def safe_url(self) -> str:
        if isinstance(self.bootstrap_servers, str):
            return get_safe_url(self.bootstrap_servers)
        return ",".join(get_safe_url(server) for server in self.bootstrap_servers)

    @staticmethod
    def extra_message_span_attributes(
        message: aiokafka.ConsumerRecord,
    ) -> dict[str, Any]:
        return {
            "messaging.kafka.message.key": message.key,
            "messaging.kafka.message.offset": message.offset,
            "messaging.kafka.destination.partition": message.partition,
        }
