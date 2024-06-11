from __future__ import annotations

from abc import ABC
from datetime import timedelta, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import anyio
import nats
import nats.js.errors
from nats.aio.client import Client
from nats.aio.msg import Msg as NatsMsg
from nats.js import JetStreamContext, api
from nats.js.api import ConsumerConfig

from eventiq.broker import Broker, R
from eventiq.exceptions import PublishError

from ...message import Message, RawMessage
from ...utils import get_safe_url, to_float, utc_now
from .settings import JetStreamSettings, NatsSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Encoder, ServerInfo, Service


class NatsMessageProxy(Message[NatsMsg]):
    @property
    def num_delivered(self) -> int | None:
        try:
            return self._message.metadata.num_delivered
        except Exception:
            return None


class AbstractNatsBroker(Broker[RawMessage, R], ABC):
    """
    :param url: Url to nats server(s)
    :param connection_options: additional connection options passed to nats.connect(...)
    :param auto_flush: auto flush messages on publish
    :param kwargs: options for base class
    """

    protocol = "nats"
    WILDCARD_ONE = "*"
    WILDCARD_MANY = ">"
    message_proxy_class = NatsMessageProxy
    Settings = NatsSettings

    def __init__(
        self,
        *,
        url: str = "nats://localhost:4444",
        connection_options: dict[str, Any] | None = None,
        auto_flush: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url
        self.connection_options = connection_options or self.default_connection_options
        self.client = Client()
        self._auto_flush = auto_flush

    @property
    def safe_url(self) -> str:
        return get_safe_url(self.url)

    @property
    def default_connection_options(self) -> dict[str, Any]:
        return {
            "error_cb": self._error_cb,
            "closed_cb": self._closed_cb,
            "reconnected_cb": self._reconnect_cb,
            "disconnected_cb": self._disconnect_cb,
            "max_reconnect_attempts": 10,
        }

    def get_info(self) -> ServerInfo:
        parsed = urlparse(self.url)
        return {
            "host": parsed.hostname,
            "protocol": parsed.scheme,
            "pathname": parsed.path,
        }

    @staticmethod
    def extra_message_span_attributes(message: NatsMsg) -> dict[str, Any]:
        try:
            return {
                "messaging.nats.sequence.consumer": message.metadata.sequence.consumer,
                "messaging.nats.sequence.stream": message.metadata.sequence.stream,
                "message.nats.num_delivered": message.metadata.num_delivered,
            }
        except Exception:
            return {}

    def parse_incoming_message(self, message: NatsMsg, encoder: Encoder) -> Any:
        return encoder.decode(message.data)

    async def _disconnect(self) -> None:
        await self.client.close()

    async def flush(self) -> None:
        await self.client.flush()

    async def _disconnect_cb(self) -> None:
        self.logger.warning("Disconnected")

    async def _reconnect_cb(self) -> None:
        self.logger.info("Reconnected")

    async def _error_cb(self, e) -> None:
        self.logger.warning(f"Broker error {e}")

    async def _closed_cb(self) -> None:
        self.logger.warning("Connection closed")

    async def _connect(self) -> None:
        await self.client.connect(self.url, **self.connection_options)

    @property
    def is_connected(self) -> bool:
        return self.client.is_connected


class NatsBroker(AbstractNatsBroker[NatsMsg, None]):
    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        await self.client.subscribe(
            subject=self.format_topic(consumer.topic),
            queue=f"{service.name}:{consumer.name}",
            cb=self.get_handler(service, consumer),
        )

    async def _publish(self, message: CloudEvent, **kwargs) -> None:
        data = self.encoder.encode(message.model_dump())
        reply = kwargs.get("reply", "")
        headers = message.headers
        headers.setdefault("Content-Type", message.content_type)
        await self.client.publish(message.topic, data, headers=headers, reply=reply)
        if self._auto_flush or kwargs.get("flush"):
            await self.flush()


class JetStreamBroker(AbstractNatsBroker[NatsMsg, api.PubAck]):
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

    async def _publish(
        self,
        message: CloudEvent,
        **kwargs,
    ) -> api.PubAck:
        data = self.encoder.encode(message)
        headers = message.headers
        headers.setdefault("Content-Type", message.content_type)
        headers.setdefault("Nats-Msg-Id", str(message.id))
        try:
            response = await self.js.publish(
                subject=message.topic,
                payload=data,
                timeout=kwargs.get("timeout"),
                stream=kwargs.get("stream"),
                headers=headers,
            )
            if self._auto_flush:
                await self.flush()
            return response
        except Exception as e:
            raise PublishError from e

    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        durable = f"{service.name}:{consumer.name}"
        config = consumer.options.get("config", ConsumerConfig())

        if config.ack_wait is None:
            ack_wait = (
                to_float(consumer.timeout) or self.default_consumer_timeout
            ) + 30
            config.ack_wait = ack_wait  # consumer timeout + 30s for .ack()
        try:
            subscription = await self.js.pull_subscribe(
                subject=self.format_topic(consumer.topic),
                durable=durable,
                config=config,
            )
        except Exception as e:
            self.logger.warning(f"Failed to create subscription: {e}")
            return

        handler = self.get_handler(service, consumer)
        batch = consumer.options.get("prefetch_count", self.prefetch_count)
        timeout = consumer.options.get("fetch_timeout", self.fetch_timeout)
        try:
            while self._connected:
                try:
                    messages = await subscription.fetch(batch=batch, timeout=timeout)
                    async with anyio.create_task_group() as tg:
                        for i, msg in enumerate(messages):
                            tg.start_soon(handler, msg, name=f"{consumer.name}-{i}")
                    await self.flush()

                except nats.js.errors.FetchTimeoutError:
                    await anyio.sleep(5)
                except Exception as e:
                    self.logger.warning(f"Cancelling consumer due to {e}")
                    return
        finally:
            if consumer.dynamic:
                await subscription.unsubscribe()

    def _should_nack(self, message: NatsMsg) -> bool:
        date = message.metadata.timestamp.replace(tzinfo=timezone.utc)
        if date < (utc_now() - timedelta(seconds=self.validate_error_delay)):
            return True
        return False

    async def _ack(self, message: Message) -> None:
        if not message._ackd:
            await message.ack()

    async def _nack(self, message: Message) -> None:
        if not message._ackd:
            await message.nak(delay=message.delay)
