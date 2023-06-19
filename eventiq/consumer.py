from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Generic, get_type_hints

from .logger import get_logger
from .settings import DEFAULT_TIMEOUT
from .types import FT, MessageHandlerT, T, Tags
from .utils import to_async

if TYPE_CHECKING:
    from .middlewares.retries import RetryStrategy


@dataclass(frozen=True)
class ForwardResponse:
    topic: str
    as_type: str = "CloudEvent"


class Consumer(ABC, Generic[T]):
    """Base consumer class"""

    event_type: T

    def __init__(
        self,
        *,
        topic: str,
        name: str,
        timeout: int = DEFAULT_TIMEOUT,
        dynamic: bool = False,
        forward_response: ForwardResponse | None = None,
        tags: Tags = None,
        retry_strategy: RetryStrategy | None = None,
        store_results: bool = False,
        parameters: dict[str, Any] | None = None,
        **options: Any,
    ):
        self._name = name
        self.topic = topic
        self.timeout = timeout
        self.dynamic = dynamic
        self.forward_response = forward_response
        self.tags = tags or []
        self.retry_strategy = retry_strategy
        self.store_results = store_results
        self.parameters = parameters or {}
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
    async def process(self, message: T) -> Any | None:
        raise NotImplementedError


class FnConsumer(Consumer[T]):
    def __init__(
        self,
        *,
        topic: str,
        fn: FT,
        name: str,
        **extra: Any,
    ) -> None:
        super().__init__(name=name, topic=topic, **extra)
        event_type = get_type_hints(fn).get("message")
        assert event_type, f"Unable to resolve type hint for 'message' in {fn.__name__}"
        self.event_type = event_type
        if not asyncio.iscoroutinefunction(fn):
            fn = to_async(fn)
        self.fn = fn

    async def process(self, message: T) -> Any | None:
        return await self.fn(message)

    @property
    def description(self) -> str:
        return self.fn.__doc__ or ""


class GenericConsumer(Consumer[T], ABC):
    def __init_subclass__(cls, **kwargs):
        if not inspect.isabstract(cls):
            cls.event_type = cls.__orig_bases__[0].__args__[0]
            if not asyncio.iscoroutinefunction(cls.process):
                cls.process = to_async(cls.process)

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
        topic: str,
        *,
        name: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        dynamic: bool = False,
        forward_response: ForwardResponse | None = None,
        tags: Tags = None,
        retry_strategy: RetryStrategy | None = None,
        store_results: bool = False,
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
                forward_response=forward_response,
                timeout=timeout,
                tags=self.tags + (tags or []),
                retry_strategy=retry_strategy,
                store_results=store_results,
                parameters=parameters,
                dynamic=dynamic,
                **options,
            )

            self.add_consumer(consumer)
            return func_or_cls

        return wrapper
