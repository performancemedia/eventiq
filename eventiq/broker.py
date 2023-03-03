from __future__ import annotations

import asyncio
import functools
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Generic

import async_timeout
from pydantic import ValidationError

from .context import context
from .exceptions import DecodeError, Reject, Retry, Skip
from .logger import LoggerMixin
from .middleware import Middleware
from .models import CloudEvent
from .settings import BrokerSettings, Settings
from .types import Encoder, RawMessage

if TYPE_CHECKING:
    from eventiq import Consumer, Service


class AbstractBroker(ABC, Generic[RawMessage]):
    @abstractmethod
    def parse_incoming_message(self, message: RawMessage) -> Any:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return broker connection status"""
        raise NotImplementedError

    @abstractmethod
    async def _publish(self, message: CloudEvent, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _start_consumer(self, service: Service, consumer: Consumer) -> None:
        raise NotImplementedError

    async def _ack(self, message: RawMessage) -> None:
        """Empty default implementation for backends that do not support explicit ack"""

    async def _nack(self, message: RawMessage, delay: int | None = None) -> None:
        """Same as for ._ack()"""


class Broker(AbstractBroker[RawMessage], LoggerMixin, ABC):
    """Base broker class
    :param description: Broker (Server) Description
    :param encoder: Encoder (Serializer) class
    :param middlewares: Optional list of middlewares
    """

    protocol: str
    Settings = BrokerSettings

    def __init__(
        self,
        *,
        description: str | None = None,
        encoder: Encoder | None = None,
        middlewares: list[Middleware] | None = None,
    ) -> None:

        if encoder is None:
            from .encoders import get_default_encoder

            encoder = get_default_encoder()
        self.description = description or type(self).__doc__
        self.encoder = encoder
        self.middlewares: list[Middleware] = middlewares or []
        self._lock = asyncio.Lock()
        self._stopped = True

    def __repr__(self):
        return type(self).__name__

    def get_handler(
        self, service: Service, consumer: Consumer
    ) -> Callable[[RawMessage], Awaitable[Any | None]]:
        async def handler(raw_message: RawMessage) -> None:
            exc: Exception | None = None
            result: Any = None
            try:
                parsed = self.parse_incoming_message(raw_message)
                message = consumer.validate_message(parsed)
                message._raw = raw_message
                token = context.set(message.context)

            except (DecodeError, ValidationError) as e:
                self.logger.exception(
                    "Parsing error Decode/Validation error", exc_info=e
                )
                await self._ack(raw_message)
                return

            try:
                await self.dispatch_before(
                    "process_message", service, consumer, message
                )
            except Skip:
                self.logger.info(f"Skipped message {message.id}")
                await self.dispatch_after("skip_message", service, consumer, message)
                await self.ack(consumer, raw_message)
                return
            try:
                async with async_timeout.timeout(consumer.timeout):
                    self.logger.info(
                        f"Running consumer {consumer.name} with message {message.id}"
                    )
                    result = await consumer.process(message)
                if consumer.forward_response and result is not None:
                    await self.publish_event(
                        CloudEvent(
                            type=consumer.forward_response.as_type,
                            topic=consumer.forward_response.topic,
                            data=result,
                            trace_id=message.trace_id,
                            source=service.name,
                        )
                    )
            # TODO: asyncio.CanceledError handling (?)
            except Exception as e:
                exc = e
            finally:
                if isinstance(exc, Reject):
                    self.logger.warning(
                        f"Message {message.id} rejected due to {exc.reason}"
                    )
                await self.dispatch_after(
                    "process_message", service, consumer, message, result, exc
                )
                if exc and isinstance(exc, Retry):
                    await self.nack(consumer, message, exc.delay)
                else:
                    await self.ack(consumer, message)
                context.reset(token)

        return handler

    async def ack(self, consumer: Consumer, message: RawMessage) -> None:
        await self.dispatch_before("ack", consumer, message)
        await self._ack(message)
        await self.dispatch_after("ack", consumer, message)

    async def nack(
        self,
        consumer: Consumer,
        message: RawMessage,
        delay: int | None = None,
    ) -> None:
        await self.dispatch_after(
            "nack",
            consumer,
            message,
        )
        await self._nack(message, delay)
        await self.dispatch_after(
            "nack",
            consumer,
            message,
        )

    async def connect(self) -> None:
        async with self._lock:
            if self._stopped:
                await self.dispatch_before("broker_connect")
                await self._connect()
                self._stopped = False
                await self.dispatch_after("broker_connect")

    async def disconnect(self) -> None:
        async with self._lock:
            if not self._stopped:
                await self.dispatch_before("broker_disconnect")
                await self._disconnect()
                self._stopped = True
                await self.dispatch_after("broker_disconnect")

    async def publish_event(self, message: CloudEvent, **kwargs: Any) -> None:
        """
        :param message: Cloud event object to send
        :param kwargs: Additional params passed to broker._publish
        :rtype: None
        """
        await self.dispatch_before("publish", message)
        await self._publish(message, **kwargs)
        await self.dispatch_after("publish", message)

    async def publish(
        self,
        topic: str,
        data: Any | None = None,
        type_: type[CloudEvent] | str = "CloudEvent",
        source: str = "",
        **kwargs: Any,
    ) -> None:
        """Publish message to broker
        :param topic: Topic to publish data
        :param data: Message content
        :param type_: Event type, name or class
        :param source: message sender (service/app name)
        :param kwargs: additional params passed to underlying broker implementation, such as headers
        :rtype: None
        """

        if isinstance(type_, str):
            cls = functools.partial(CloudEvent, type=type_)
        else:
            cls = type_  # type: ignore

        message: CloudEvent = cls(
            content_type=self.encoder.CONTENT_TYPE,
            topic=topic,
            data=data,
            source=source,
        )
        await self.publish_event(message, **kwargs)

    async def start_consumer(self, service: Service, consumer: Consumer):
        await self.dispatch_before("consumer_start", service, consumer)
        await self._start_consumer(service, consumer)
        await self.dispatch_after("consumer_start", service, consumer)

    def add_middleware(self, middleware: Middleware) -> None:
        if not isinstance(middleware, Middleware):
            raise TypeError(f"Middleware expected, got {type(middleware)}")
        self.middlewares.append(middleware)

    async def _dispatch(self, full_event: str, *args, **kwargs) -> None:
        for m in self.middlewares:
            try:
                await getattr(m, full_event)(self, *args, **kwargs)
            except Skip:
                raise
            except Exception as e:
                self.logger.exception("Unhandled middleware exception", exc_info=e)

    async def dispatch_before(self, event: str, *args, **kwargs) -> None:
        await self._dispatch(f"before_{event}", *args, **kwargs)

    async def dispatch_after(self, event: str, *args, **kwargs) -> None:
        await self._dispatch(f"after_{event}", *args, **kwargs)

    @classmethod
    def from_env(
        cls,
        description: str | None = None,
        middlewares: list[Middleware] | None = None,
        **kwargs,
    ) -> Broker:
        settings = Settings()
        broker_cls: type[Broker] = settings.get_broker_class()
        broker_settings = broker_cls.Settings(
            description=description, middlewares=middlewares, **kwargs
        )
        instance = broker_cls(**broker_settings.dict())
        return instance
