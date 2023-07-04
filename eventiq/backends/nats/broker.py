from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import anyio
import nats
from nats.aio.client import Client
from nats.aio.msg import Msg as NatsMsg
from nats.errors import NotJSMessageError
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig

from eventiq.broker import Broker
from eventiq.exceptions import BrokerError, PublishError

from ...message import Message
from ...utils import retry
from .settings import JetStreamSettings, NatsSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Service


class JsMessageProxy(Message[NatsMsg]):
    def __init__(self, message: NatsMsg):
        super().__init__(message)

    @property
    def num_delivered(self) -> int | None:
        try:
            return self._message.metadata.num_delivered
        except NotJSMessageError:
            return None


class NatsBroker(Broker[NatsMsg]):
    """
    :param url: Url to nats server(s)
    :param connection_options: additional connection options passed to nats.connect(...)
    :param auto_flush: auto flush messages on publish
    :param kwargs: options for base class
    """

    protocol = "nats"
    WILDCARD_ONE = "*"
    WILDCARD_MANY = ">"

    def __init__(
        self,
        *,
        url: str = "nats://localhost:4444",
        connection_options: dict[str, Any] | None = None,
        auto_flush: bool = True,
        **kwargs: Any,
    ) -> None:

        super().__init__(**kwargs)
        self.url = url
        self.connection_options = connection_options or {}
        self.connection_options.setdefault("pending_size", 0)
        self._auto_flush = auto_flush
        self.client = Client()

    def parse_incoming_message(self, message: NatsMsg) -> Any:
        return self.encoder.decode(message.data)

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        await self.client.subscribe(
            subject=self.format_topic(consumer.topic),
            queue=f"{service.name}:{consumer.name}",
            cb=self.get_handler(service, consumer),
        )

    async def _disconnect(self) -> None:
        await self.client.close()

    async def flush(self):
        await self.client.flush()

    async def _connect(self) -> None:
        await self.client.connect(self.url, **self.connection_options)

    @retry(max_retries=3)
    async def _publish(self, message: CloudEvent, **kwargs) -> None:
        data = self.encoder.encode(message.dict())
        await self.client.publish(message.topic, data, **kwargs)
        if self._auto_flush:
            await self.client.flush()

    @property
    def is_connected(self) -> bool:
        return self.client.is_connected

    Settings = NatsSettings


class JetStreamBroker(NatsBroker):
    """
    NatsBroker with JetStream enabled
    :param prefetch_count: default number of messages to prefetch
    :param fetch_timeout: timeout for subscription pull
    :param jetstream_options: additional options passed to nc.jetstream(...)
    :param kwargs: all other options for base classes NatsBroker, Broker
    """

    Settings = JetStreamSettings

    def __init__(
        self,
        *,
        prefetch_count: int = 10,
        fetch_timeout: int = 10,
        jetstream_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:

        super().__init__(**kwargs)
        self.prefetch_count = prefetch_count
        self.fetch_timeout = fetch_timeout
        self.jetstream_options = jetstream_options or {}
        self.js = JetStreamContext(self.client, **self.jetstream_options)

    @property
    def message_proxy_class(self) -> type[Message]:
        return JsMessageProxy

    @retry(max_retries=3)
    async def _publish(
        self,
        message: CloudEvent,
        **kwargs,
    ) -> None:
        data = self.encoder.encode(message)
        headers = kwargs.get("headers", {})
        timeout = kwargs.get("timeout")
        stream = kwargs.get("stream")
        headers.setdefault("Content-Type", self.encoder.CONTENT_TYPE)
        headers["Nats-Msg-Id"] = str(message.id)
        try:
            await self.js.publish(
                subject=message.topic,
                payload=data,
                timeout=timeout,
                stream=stream,
                headers=headers,
            )
            if self._auto_flush:
                await self.client.flush()
        except Exception as e:
            raise PublishError from e

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        durable = f"{service.name}:{consumer.name}"
        config = consumer.options.get("config", ConsumerConfig())
        config.ack_wait = consumer.timeout + 10  # consumer timeout + 10s for .ack()
        try:
            subscription = await self.js.pull_subscribe(
                subject=self.format_topic(consumer.topic),
                durable=durable,
                config=config,
            )
        except Exception as e:
            raise BrokerError(
                f"Error creating subscription for consumer {consumer.name} and topic {consumer.topic}"
            ) from e

        handler = self.get_handler(service, consumer)
        batch = consumer.options.get("prefetch_count", self.prefetch_count)
        timeout = consumer.options.get("fetch_timeout", self.fetch_timeout)
        try:
            while self._running:
                try:
                    messages = await subscription.fetch(batch=batch, timeout=timeout)
                    async with anyio.create_task_group() as tg:
                        for msg in messages:
                            tg.start_soon(handler, msg)
                except nats.errors.TimeoutError:
                    await asyncio.sleep(5)
        except Exception:
            self.logger.exception("Cancelling consumer")
        finally:
            if consumer.dynamic:
                await subscription.unsubscribe()

    async def _ack(self, message: Message) -> None:
        if not message._ackd:
            await message.ack()

    async def _nack(self, message: Message) -> None:
        if not message._ackd:
            await message.nak(delay=message.delay)
