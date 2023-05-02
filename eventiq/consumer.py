from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, get_type_hints

from .defaults import DEFAULT_CONSUMER_TIME_LIMIT
from .logger import get_logger
from .types import FT, MessageHandlerT, T
from .utils.functools import run_async


@dataclass(frozen=True)
class ForwardResponse:
    topic: str
    as_type: str = "CloudEvent"


class Consumer(ABC, Generic[T]):
    """ """

    event_type: T

    def __init__(
        self,
        *,
        topic: str,
        name: str,
        timeout: int = DEFAULT_CONSUMER_TIME_LIMIT,
        dynamic: bool = False,
        forward_response: ForwardResponse | None = None,
        **options: Any,
    ):
        self._name = name
        self.topic = topic
        self.timeout = timeout
        self.dynamic = dynamic
        self.forward_response = forward_response
        self.options: dict[str, Any] = options
        self.logger = get_logger(__name__, name)

    def validate_message(self, message: Any) -> T:
        return self.event_type.parse_obj(message)

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def process(self, message: T):
        raise NotImplementedError


class FnConsumer(Consumer[T]):
    def __init__(
        self,
        *,
        topic: str,
        fn: FT,
        name: str | None = None,
        **options: Any,
    ) -> None:
        super().__init__(name=name or fn.__name__, topic=topic, **options)
        event_type = get_type_hints(fn).get("message")
        assert event_type, f"Unable to resolve type hint for 'message' in {fn.__name__}"
        self.event_type = event_type
        if not asyncio.iscoroutinefunction(fn):
            fn = run_async(fn)
        self.fn = fn

    async def process(self, message: T) -> Any | None:
        self.logger.info("Processing message <%s>", message.type)
        result = await self.fn(message)
        self.logger.info("Finished processing <%s>", message.type)
        return result

    @property
    def description(self) -> str:
        return self.fn.__doc__ or ""


class GenericConsumer(Consumer[T], ABC):
    def __init__(self, *, topic: str, name: str | None = None, **options: Any):

        super().__init__(
            name=name or str(getattr(type(self), "name", type(self).__name__)),
            topic=topic,
            **options,
        )

    def __init_subclass__(cls, **kwargs):
        if "abstract" not in kwargs:
            cls.event_type = cls.__orig_bases__[0].__args__[0]
            if not hasattr(cls, "name"):
                cls.name = cls.__name__
            if not asyncio.iscoroutinefunction(cls.process):
                cls.process = run_async(cls.process)

    @property
    def description(self) -> str:
        return self.__doc__ or ""


class ConsumerGroup:
    def __init__(self, consumers: dict[str, Consumer] | None = None):
        self.consumers = consumers or {}

    def add_consumer(self, consumer: Consumer) -> None:
        self.consumers[consumer.name] = consumer

    def add_consumer_group(self, other: ConsumerGroup) -> None:
        self.consumers.update(other.consumers)

    def subscribe(
        self,
        topic: str,
        *,
        name: str | None = None,
        timeout: int = 120,
        dynamic: bool = False,
        forward_response: ForwardResponse | None = None,
        **options,
    ):
        def wrapper(func_or_cls: MessageHandlerT) -> MessageHandlerT:
            cls: type[Consumer] = FnConsumer
            if isinstance(func_or_cls, type) and issubclass(
                func_or_cls, GenericConsumer
            ):
                cls = func_or_cls
            elif callable(func_or_cls):
                options["fn"] = func_or_cls
            else:
                raise TypeError("Expected function or GenericConsumer")

            consumer = cls(
                topic=topic,
                name=name,  # type: ignore
                timeout=timeout,
                dynamic=dynamic,
                forward_response=forward_response,
                **options,
            )
            self.add_consumer(consumer)
            return func_or_cls

        return wrapper
