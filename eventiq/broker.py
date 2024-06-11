from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, Callable, Generic, Literal, TypeVar

import anyio
from pydantic import ValidationError

from .encoder import Encoder
from .exceptions import ConsumerTimeoutError, DecodeError, Fail, Retry, Skip
from .imports import import_from_string
from .logger import LoggerMixin
from .message import Message, RawMessage
from .middleware import Middleware
from .models import CloudEvent
from .settings import BrokerSettings
from .types import Timeout
from .utils import format_topic, to_float

if TYPE_CHECKING:
    from eventiq import Consumer, ServerInfo, Service

TOPIC_PATTERN = re.compile(r"{\w+}")

R = TypeVar("R", bound=Any)

DefaultAction = Literal["ack", "nack"]


class AbstractBroker(Generic[RawMessage, R], ABC):
    @abstractmethod
    def get_info(self) -> ServerInfo:
        raise NotImplementedError

    @abstractmethod
    def parse_incoming_message(self, message: RawMessage, encoder: Encoder) -> Any:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return broker connection status"""
        raise NotImplementedError

    @abstractmethod
    async def _publish(self, message: CloudEvent, **kwargs) -> R:
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

    @abstractmethod
    def _should_nack(self, message: RawMessage) -> bool:
        raise NotImplementedError


class Broker(AbstractBroker[RawMessage, R], LoggerMixin, ABC):
    """Base broker class
    :param description: Broker (Server) Description
    :param encoder: Encoder (Serializer) class
    :param middlewares: Optional list of middlewares
    """

    protocol: str
    protocol_version: str = ""
    message_proxy_class: type[Message[RawMessage]] = Message

    Settings = BrokerSettings

    WILDCARD_ONE: str
    WILDCARD_MANY: str

    def __init__(
        self,
        *,
        description: str | None = None,
        encoder: Encoder | type[Encoder] | None = None,
        middlewares: list[Middleware] | None = None,
        default_consumer_timeout: Timeout = 300,
        default_on_exc: DefaultAction = "nack",
        tags: list[str] | None = None,
        asyncapi_extra: dict[str, Any] | None = None,
        validate_error_delay: int = 3600 * 12,
    ) -> None:
        if encoder is None:
            from .encoders import get_default_encoder

            encoder = get_default_encoder()
        elif isinstance(encoder, type):
            encoder = encoder()
        self.encoder = encoder

        self.description = description or type(self).__name__
        self.middlewares: list[Middleware] = middlewares or []
        self.default_consumer_timeout = to_float(default_consumer_timeout)
        self.default_on_exc = default_on_exc
        self.tags = tags
        self.async_api_extra = asyncapi_extra or {}
        self._lock = anyio.Lock()
        self._connected = False
        self.validate_error_delay = validate_error_delay

    def __repr__(self):
        return type(self).__name__

    async def _handle_message_finalization(
        self,
        service: Service,
        consumer: Consumer,
        message: CloudEvent,
        result: Any,
        exc: Exception | None,
    ):
        self.logger.info(
            f"Finished running consumer {consumer.name} with message {message.id}"
        )
        await self.dispatch_after(
            "process_message", service, consumer, message, result, exc
        )
        if exc is None or message.failed:
            await self.ack(service, consumer, message.raw)
            return
        if isinstance(exc, Fail):
            self.logger.warning(f"Failing message {message.id} due to {exc}")
            await self.ack(service, consumer, message.raw)
            return
        if isinstance(exc, Skip):
            self.logger.info(f"Skipping message {message.id} due to {exc}")
            await self.dispatch_after("skip_message", service, consumer, message)
            await self.ack(service, consumer, message.raw)
            return
        if isinstance(exc, Retry):
            self.logger.info(
                f"Retrying message {message.id} in {exc.delay} due to {exc.reason}"
            )
            await self.nack(service, consumer, message.raw)
            return

        await getattr(self, self.default_on_exc)(service, consumer, message.raw)

    def _should_nack(self, message: RawMessage) -> bool:
        return False

    def get_handler(
        self, service: Service, consumer: Consumer
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        consumer_timeout = to_float(consumer.timeout) or self.default_consumer_timeout
        encoder = consumer.encoder or self.encoder

        async def handler(raw_message: RawMessage) -> None:
            exc: Exception | None = None
            result = None
            msg = self.message_proxy_class(raw_message)
            try:
                parsed = self.parse_incoming_message(raw_message, encoder)
                message = consumer.validate_message(parsed)
                message.raw = msg
                message.service = service
            except (DecodeError, ValidationError) as e:
                self.logger.error(
                    f"Failed to validate message {raw_message}.", exc_info=e
                )
                if self._should_nack(raw_message):
                    msg.delay = self.validate_error_delay
                    await self.nack(service, consumer, msg)
                else:
                    await self.ack(service, consumer, msg)
                return
            try:
                await self.dispatch_before(
                    "process_message", service, consumer, message
                )
                self.logger.info(
                    f"Running consumer {consumer.name} with message {message.id}"
                )
                with anyio.move_on_after(consumer_timeout) as scope:
                    result = await consumer.process(message)
                    if consumer.reply_to and result:
                        for broker, spec in consumer.reply_to.items():
                            ce = spec.type(topic=spec.topic, data=result)
                            await service.publish(ce, broker=broker)
                if scope.cancel_called:
                    self.logger.warning(
                        f"Consumer {consumer.name} timed out on message {message.id}"
                    )
                    exc = ConsumerTimeoutError()
            except Exception as e:
                exc = e
            finally:
                await self._handle_message_finalization(
                    service, consumer, message, result, exc
                )

        return handler

    async def ack(self, service: Service, consumer: Consumer, message: Message) -> None:
        await self.dispatch_before("ack", service, consumer, message)
        await self._ack(message)
        await self.dispatch_after("ack", service, consumer, message)

    async def nack(
        self,
        service: Service,
        consumer: Consumer,
        message: Message,
    ) -> None:
        await self.dispatch_after(
            "nack",
            service,
            consumer,
            message,
        )
        await self._nack(message)
        await self.dispatch_after(
            "nack",
            service,
            consumer,
            message,
        )

    async def connect(self) -> None:
        async with self._lock:
            if not self._connected:
                await self.dispatch_before("broker_connect")
                await self._connect()
                self._connected = True
                await self.dispatch_after("broker_connect")

    async def disconnect(self) -> None:
        async with self._lock:
            if self._connected:
                await self.dispatch_before("broker_disconnect")
                self._connected = False
                await self._disconnect()
                await self.dispatch_after("broker_disconnect")

    async def publish(self, message: CloudEvent, **kwargs: Any) -> R:
        """
        :param message: Cloud event object to send
        :param kwargs: Additional params passed to broker._publish
        :rtype: None
        """
        if not self.is_connected:
            await self.connect()
        await self.dispatch_before("publish", message, **kwargs)
        res = await self._publish(message, **kwargs)
        await self.dispatch_after("publish", message, **kwargs)
        return res

    async def start_consumer(self, service: Service, consumer: Consumer):
        await self.dispatch_before("consumer_start", service, consumer)
        await self._start_consumer(service, consumer)
        await self.dispatch_after("consumer_start", service, consumer)

    def add_middleware(self, middleware: Middleware | type[Middleware]) -> None:
        if isinstance(middleware, type):
            middleware = middleware()
        self.middlewares.append(middleware)

    def add_middlewares(self, middlewares: list[Middleware | type[Middleware]]) -> None:
        for m in middlewares:
            self.add_middleware(m)

    async def _dispatch(self, full_event: str, *args, **kwargs) -> None:
        for middleware in self.middlewares:
            try:
                await getattr(middleware, full_event)(self, *args, **kwargs)
            except middleware.throws as e:
                self.logger.warning("Unhandled middleware exception", exc_info=e)

    async def dispatch_before(self, event: str, *args, **kwargs) -> None:
        await self._dispatch(f"before_{event}", *args, **kwargs)

    async def dispatch_after(self, event: str, *args, **kwargs) -> None:
        await self._dispatch(f"after_{event}", *args, **kwargs)

    @classmethod
    def from_settings(cls, settings: BrokerSettings, **kwargs: Any) -> Broker:
        return cls(**settings.model_dump(), **kwargs)

    @classmethod
    def _from_env(cls, **kwargs) -> Broker:
        return cls.from_settings(cls.Settings(**kwargs))

    @classmethod
    def from_env(
        cls,
        **kwargs,
    ) -> Broker:
        if cls == Broker:
            type_name = os.getenv("BROKER_CLASS", "eventiq.backends.stub:StubBroker")
            broker_type = import_from_string(type_name)
        else:
            broker_type = cls
        return broker_type._from_env(**kwargs)

    @property
    def safe_url(self) -> str:
        return ""

    @staticmethod
    def extra_message_span_attributes(message: RawMessage) -> dict[str, Any]:
        return {}

    def format_topic(self, topic: str) -> str:
        return format_topic(topic, self.WILDCARD_ONE, self.WILDCARD_MANY)

    async def _ack(self, message: Message) -> None:
        """Empty default implementation for backends that do not support explicit ack"""

    async def _nack(self, message: Message) -> None:
        """Reject (requeue) message. Defaults to no-op like ._ack()"""
