from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, TypeVar, Union

from .encoder import Encoder
from .logger import get_logger
from .models import CloudEvent
from .types import Tags
from .utils import resolve_message_type_hint, to_async

if TYPE_CHECKING:
    from .middlewares.retries import RetryStrategy

CE = TypeVar("CE", bound=CloudEvent)

FT = Callable[["CloudEvent"], Union[Awaitable[Optional[Any]], Optional["CloudEvent"]]]
MessageHandlerT = Union[type["GenericConsumer"], FT]


@dataclass
class ReplyTo:
    brokers: tuple[str] = ("default",)


class Consumer(ABC, Generic[CE]):
    """Base consumer class"""

    event_type: CE
    name: str

    def __init__(
        self,
        *,
        topic: str | None = None,
        brokers: tuple[str] = ("default",),
        timeout: int | None = None,
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

    @property
    def logger(self):
        return get_logger(__name__, self.name)

    def validate_message(self, message: Any) -> CloudEvent:
        return self.event_type.model_validate(message)

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def process(self, message: CE) -> CloudEvent | None:
        raise NotImplementedError


class FnConsumer(Consumer[CE]):
    def __init__(
        self,
        *,
        topic: str,
        fn: FT,
        name: str,
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
        self.name = name
        super().__init__(name=name, topic=topic, **extra)

    async def process(self, message: CE) -> CloudEvent | None:
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
            if not hasattr(cls, "name") or cls.name is None:
                cls.name = cls.__name__

    @property
    def description(self) -> str:
        return self.__doc__ or ""


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
        timeout: int | None = None,
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
            cls: type[Consumer] = FnConsumer
            if isinstance(func_or_cls, type) and issubclass(
                func_or_cls, GenericConsumer
            ):
                cls = func_or_cls
                name_ = name or str(getattr(func_or_cls, "name", type(self).__name__))
            elif callable(func_or_cls):
                options["fn"] = func_or_cls
                name_ = name or func_or_cls.__name__
            else:
                raise TypeError("Expected function or GenericConsumer")
            for k, v in self.options.items():
                options.setdefault(k, v)

            consumer = cls(
                topic=topic,
                name=name_,
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
