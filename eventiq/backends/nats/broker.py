from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import nats
from nats.aio.msg import Msg as NatsMsg
from nats.js import JetStreamContext

from eventiq.broker import Broker
from eventiq.exceptions import BrokerError, PublishError
from eventiq.utils.functools import retry_async

from ...message import Message
from .settings import JetStreamSettings, NatsSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Service


class NatsMessageProxy(Message[NatsMsg]):
    def __init__(self, message: NatsMsg):
        super().__init__(message)
        self._num_delivered = message.metadata.num_delivered


class NatsBroker(Broker[NatsMsg]):
    """
    :param url: Url to nats server(s)
    :param connection_options: additional connection options passed to nats.connect(...)
    :param auto_flush: auto flush messages on publish
    :param kwargs: options for base class
    """

    protocol = "nats"

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
        self._auto_flush = auto_flush
        self._nc = None

    @property
    def message_proxy_class(self) -> type[Message]:
        return NatsMessageProxy

    @property
    def nc(self) -> nats.NATS:
        if self._nc is None:
            raise BrokerError("Broker not connected. Call await broker.connect() first")
        return self._nc

    def parse_incoming_message(self, message: NatsMsg) -> Any:
        return self.encoder.decode(message.data)

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        await self.nc.subscribe(
            subject=consumer.topic,
            queue=f"{service.name}:{consumer.name}",
            cb=self.get_handler(service, consumer),
        )

    async def _disconnect(self) -> None:
        await self.nc.close()

    async def flush(self):
        await self.nc.flush()

    @retry_async(max_retries=3)
    async def _connect(self) -> None:
        self._nc = await nats.connect(self.url, **self.connection_options)

    @retry_async(max_retries=3)
    async def _publish(self, message: CloudEvent, **kwargs) -> None:
        data = self.encoder.encode(message.dict())
        await self.nc.publish(message.topic, data, **kwargs)
        if self._auto_flush:
            await self.nc.flush()

    @property
    def is_connected(self) -> bool:
        return self.nc.is_connected

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
        self._js = None

    @property
    def js(self) -> JetStreamContext:
        if not (self._nc and self._js):
            raise BrokerError("Broker not connected")
        return self._js

    async def _connect(self) -> None:
        await super()._connect()
        self._js = self.nc.jetstream(**self.jetstream_options)

    @retry_async(max_retries=3)
    async def _publish(
        self,
        message: CloudEvent,
        timeout: float | None = None,
        stream: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        data = self.encoder.encode(message)
        headers = headers or {}
        headers.setdefault("Content-Type", self.encoder.CONTENT_TYPE)
        try:
            await self.js.publish(
                subject=message.topic,
                payload=data,
                timeout=timeout,
                stream=stream,
                headers=headers,
            )
        except Exception as e:
            raise PublishError from e

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        durable = f"{service.name}:{consumer.name}"
        subscription = await self.js.pull_subscribe(
            subject=consumer.topic,
            durable=durable,
            config=consumer.options.get("config"),
        )
        handler = self.get_handler(service, consumer)
        batch = consumer.options.get("prefetch_count", self.prefetch_count)
        timeout = consumer.options.get("fetch_timeout", self.fetch_timeout)
        try:
            while not self._stopped:
                try:
                    messages = await subscription.fetch(batch=batch, timeout=timeout)
                    tasks = [asyncio.create_task(handler(message)) for message in messages]  # type: ignore
                    await asyncio.gather(*tasks, return_exceptions=True)
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
