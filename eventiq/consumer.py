from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar, Union

from .encoder import Encoder
from .logger import get_logger
from .models import CloudEvent
from .types import Tags, Timeout
from .utils import resolve_message_type_hint, to_async

if TYPE_CHECKING:
    from .middlewares.retries import RetryStrategy

CE = TypeVar("CE", bound=CloudEvent)

FT = Callable[[CloudEvent], Awaitable[Any]]


# @dataclass
# class ReplyTo:
#     brokers: tuple[str] = ("default",)


@dataclass
class ResponseSpec:
    type: type[CloudEvent]
    topic: str | None = None


BrokerName = str

ReplyTo = dict[BrokerName, ResponseSpec]


class Consumer(ABC, Generic[CE]):
    """Base consumer class"""

    event_type: CE

    def __init__(
        self,
        *,
        name: str,
        topic: str | None = None,
        brokers: tuple[str] = ("default",),
        timeout: Timeout | None = None,
        dynamic: bool = False,
        reply_to: ReplyTo | None = None,
        tags: Tags = None,
        retry_strategy: RetryStrategy | None = None,
        store_results: bool = False,
        encoder: Encoder | None = None,
        parameters: dict[str, Any] | None = None,
        **options: Any,
    ):
        topic = topic or self.event_type.get_default_topic()
        if not topic:
            raise ValueError("Topic expected")
        self.name = name
        self.brokers = brokers
        self.topic = topic
        self.timeout = timeout
        self.dynamic = dynamic
        self.reply_to = reply_to
        self.tags = tags or []
        self.retry_strategy = retry_strategy
        self.store_results = store_results
        self.encoder = encoder
        self.parameters = parameters or {}
        self.options: dict[str, Any] = options
        self.logger = get_logger(__name__, self.name)

    def validate_message(self, message: Any) -> CloudEvent:
        return self.event_type.model_validate(message)

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def process(self, message: CE) -> Any:
        raise NotImplementedError


class FnConsumer(Consumer[CE]):
    def __init__(
        self,
        *,
        fn: FT,
        **extra: Any,
    ) -> None:
        event_type = resolve_message_type_hint(fn)
        if not event_type:
            raise TypeError(
                "Unable to resolve type hint for 'message' in %s", fn.__name__
            )
        self.event_type = event_type
        if not asyncio.iscoroutinefunction(fn):
            fn = to_async(fn)
        self.fn = fn
        super().__init__(**extra)

    async def process(self, message: CE) -> Any:
        return await self.fn(message)

    @property
    def description(self) -> str:
        return self.fn.__doc__ or ""


class GenericConsumer(Consumer[CE], ABC):
    def __init_subclass__(cls, **kwargs):
        if not inspect.isabstract(cls):
            cls.event_type = cls.__orig_bases__[0].__args__[0]
            if not asyncio.iscoroutinefunction(cls.process):
                cls.process = to_async(cls.process)

    @property
    def description(self) -> str:
        return self.__doc__ or ""


MessageHandlerT = Union[type[GenericConsumer], FT]


class ConsumerGroup:
    def __init__(
        self, consumers: dict[str, Consumer] | None = None, tags: Tags = None, **options
    ):
        self.consumers = consumers or {}
        self.tags = tags or []
        self.options = options

    def add_consumer(self, consumer: Consumer) -> None:
        self.consumers[consumer.name] = consumer

    def add_consumer_group(self, other: ConsumerGroup) -> None:
        self.consumers.update(other.consumers)

    def subscribe(
        self,
        topic: str | None = None,
        *,
        name: str | None = None,
        brokers: tuple[str] = ("default",),
        timeout: Timeout | None = None,
        dynamic: bool = False,
        reply_to: ReplyTo | None = None,
        tags: Tags = None,
        retry_strategy: RetryStrategy | None = None,
        store_results: bool = False,
        encoder: Encoder | None = None,
        parameters: dict[str, Any] | None = None,
        **options,
    ) -> Callable[[MessageHandlerT], MessageHandlerT]:
        def wrapper(func_or_cls: MessageHandlerT) -> MessageHandlerT:
            nonlocal name
            cls: type[Consumer] = FnConsumer
            if inspect.isfunction(func_or_cls):
                options["fn"] = func_or_cls
                if name is None:
                    name = func_or_cls.__name__
            elif isinstance(func_or_cls, type) and issubclass(
                func_or_cls, GenericConsumer
            ):
                cls = func_or_cls
                if name is None:
                    name = getattr(cls, "name", cls.__name__)
            else:
                raise TypeError("Expected function or GenericConsumer")
            for k, v in self.options.items():
                options.setdefault(k, v)

            consumer = cls(
                topic=topic,
                name=name,
                brokers=brokers,
                reply_to=reply_to,
                timeout=timeout,
                dynamic=dynamic,
                tags=self.tags + (tags or []),
                retry_strategy=retry_strategy,
                store_results=store_results,
                encoder=encoder,
                parameters=parameters,
                **options,
            )

            self.add_consumer(consumer)
            return func_or_cls

        return wrapper
