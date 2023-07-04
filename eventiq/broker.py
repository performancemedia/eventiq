from __future__ import annotations

import asyncio
import os
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Generic

import anyio
from pydantic import ValidationError

from .context import _current_message, _current_service
from .exceptions import DecodeError, Fail, Skip
from .imports import import_from_string
from .logger import LoggerMixin
from .message import Message
from .middleware import Middleware
from .models import CloudEvent
from .settings import BrokerSettings
from .types import Encoder, RawMessage

if TYPE_CHECKING:
    from eventiq import Consumer, Service

TOPIC_PATTERN = re.compile(r"{\w+}")


class Broker(Generic[RawMessage], LoggerMixin, ABC):
    """Base broker class
    :param description: Broker (Server) Description
    :param encoder: Encoder (Serializer) class
    :param middlewares: Optional list of middlewares
    """

    protocol: str
    protocol_version: str | None = None

    Settings = BrokerSettings

    WILDCARD_ONE: str
    WILDCARD_MANY: str

    def __init__(
        self,
        *,
        description: str | None = None,
        encoder: Encoder | type[Encoder] | None = None,
        middlewares: list[Middleware] | None = None,
    ) -> None:

        if encoder is None:
            from .encoders import get_default_encoder

            encoder = get_default_encoder()
        elif isinstance(encoder, type):
            encoder = encoder()
        self.encoder = encoder

        self.description = description or type(self).__name__
        self.middlewares: list[Middleware] = middlewares or []
        self._lock = anyio.Lock()
        self._running = False

    def __repr__(self):
        return type(self).__name__

    @property
    def message_proxy_class(self) -> type[Message]:
        return Message

    def get_handler(
        self, service: Service, consumer: Consumer
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        async def handler(raw_message: RawMessage) -> None:
            exc: Exception | None = None
            result: Any = None
            msg = self.message_proxy_class(raw_message)
            s_token = _current_service.set(service)
            try:
                parsed = self.parse_incoming_message(raw_message)
                message = consumer.validate_message(parsed)
                message.set_raw(msg)
            except (DecodeError, ValidationError) as e:
                self.logger.exception("Message parsing error", exc_info=e)
                msg.fail()
                await self.ack(service, consumer, msg)
                return
            m_token = _current_message.set(message)
            try:
                await self.dispatch_before(
                    "process_message", service, consumer, message
                )
            except Skip:
                self.logger.info(f"Skipped message {message.id}")
                await self.dispatch_after("skip_message", service, consumer, message)
                await self.ack(service, consumer, msg)
                return
            try:
                self.logger.info(
                    f"Running consumer {consumer.name} with message {message.id}"
                )
                async with anyio.move_on_after(consumer.timeout) as scope:
                    result = await consumer.process(message)

                    if consumer.forward_response and result is not None:
                        await self.publish(
                            CloudEvent(
                                type=consumer.forward_response.as_type,
                                topic=consumer.forward_response.topic,
                                data=result,
                                source=service.name,
                            )
                        )
                if scope.cancel_called:
                    exc = asyncio.TimeoutError()
            except Exception as e:
                self.logger.warning(
                    f"Exception in {consumer.name} <{type(e).__name__}> {e}"
                )
                exc = e
            finally:
                self.logger.info(f"Finished running consumer {consumer.name}")
                async with anyio.move_on_after(10, shield=True):
                    await self.dispatch_after(
                        "process_message", service, consumer, message, result, exc
                    )
                    if exc is None or isinstance(exc, Fail) or msg.failed:
                        await self.ack(service, consumer, msg)
                    else:
                        await self.nack(service, consumer, msg)
                _current_service.reset(s_token)
                _current_message.reset(m_token)

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

    async def connect(self, **kwargs) -> None:
        async with self._lock:
            if not self._running:
                await self.dispatch_before("broker_connect")
                await self._connect()
                self._running = True
                await self.dispatch_after("broker_connect")

    async def disconnect(self) -> None:
        async with self._lock:
            if self._running:
                await self.dispatch_before("broker_disconnect")
                self._running = False
                await self._disconnect()
                await self.dispatch_after("broker_disconnect")

    async def publish(self, message: CloudEvent, **kwargs: Any) -> None:
        """
        :param message: Cloud event object to send
        :param kwargs: Additional params passed to broker._publish
        :rtype: None
        """
        await self.dispatch_before("publish", message)
        await self._publish(message, **kwargs)
        await self.dispatch_after("publish", message)

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
    def from_settings(cls, settings: BrokerSettings, **kwargs: Any) -> Broker:
        return cls(**settings.dict(), **kwargs)

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

    async def _ack(self, message: Message) -> None:
        """Empty default implementation for backends that do not support explicit ack"""

    async def _nack(self, message: Message) -> None:
        """Same as for ._ack()"""

    def format_topic(self, topic: str) -> str:
        result = []
        for k in topic.split("."):
            if re.fullmatch(TOPIC_PATTERN, k):
                result.append(self.WILDCARD_ONE)
            elif k in {"*", ">"}:
                result.append(self.WILDCARD_MANY)
            else:
                result.append(k)
        return ".".join(filter(None, result))
