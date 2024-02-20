from __future__ import annotations

import asyncio
import functools
from abc import ABC, abstractmethod
from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Callable

import anyio
from anyio import CancelScope

from .asyncapi import PUBLISH_REGISTRY
from .consumer import Consumer, ConsumerGroup, ReplyTo
from .logger import LoggerMixin
from .models import CloudEvent
from .utils import generate_instance_id

if TYPE_CHECKING:
    from eventiq import Broker, Encoder

    from .asyncapi import PublishInfo
    from .middlewares.retries import RetryStrategy
    from .types import TagMeta, Tags, Timeout


class AbstractService(ABC):
    @abstractmethod
    async def start(self, scope: CancelScope | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError

    async def __aenter__(self):
        self._task = asyncio.create_task(self.start())
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, *exc_info):
        with suppress(asyncio.exceptions.CancelledError):
            self._task.cancel()
            await self._task
            await self.stop()


class Service(AbstractService, LoggerMixin):
    """Logical group of consumers. Provides group (queue) name and handles versioning"""

    def __init__(
        self,
        name: str,
        broker: Broker | None = None,
        title: str | None = None,
        version: str = "0.1.0",
        description: str = "",
        tags_metadata: list[TagMeta] | None = None,
        instance_id_generator: Callable[[], str] | None = None,
        base_event_class: type[CloudEvent] = CloudEvent,
        publish_info: Sequence[PublishInfo] = (),
        brokers: dict[str, Broker] | None = None,
        context: dict[str, Any] | None = None,
        async_api_extra: dict[str, Any] | None = None,
    ):
        self._brokers: dict[str, Broker] = {}
        if broker:
            self._brokers["default"] = broker
        if brokers:
            self._brokers.update(brokers)

        self.name = name
        self.title = title or name.title()
        self.version = version
        self.description = description
        self.tags_metadata = tags_metadata or []
        self.id = (instance_id_generator or generate_instance_id)()
        self.consumer_group = ConsumerGroup()
        self.context = context or {}
        self.base_event_class = base_event_class
        self.async_api_extra = async_api_extra or {}

        for p in publish_info:
            PUBLISH_REGISTRY[p.event_type.__name__] = p

    @property
    def default_broker(self) -> Broker:
        return self._brokers["default"]

    @property
    def brokers(self):
        return self._brokers.values()

    def get_brokers(self):
        return self._brokers.items()

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
        **options: Any,
    ):
        return self.consumer_group.subscribe(
            topic=topic,
            name=name,
            brokers=brokers,
            timeout=timeout,
            dynamic=dynamic,
            reply_to=reply_to,
            tags=tags,
            retry_strategy=retry_strategy,
            store_results=store_results,
            encoder=encoder,
            parameters=parameters,
            **options,
        )

    def add_consumer(self, consumer: Consumer):
        self.consumer_group.add_consumer(consumer)

    def add_consumer_group(self, consumer_group: ConsumerGroup) -> None:
        self.consumer_group.add_consumer_group(consumer_group)

    async def send(
        self,
        topic: str,
        type_: type[CloudEvent] | str = "CloudEvent",
        data: Any | None = None,
        broker: str = "default",
        **kwargs,
    ):
        if isinstance(type_, str):
            cls = self.base_event_class
            kwargs["type"] = type_
        else:
            cls = type_
        _broker = self._brokers[broker]

        message: CloudEvent = cls(
            content_type=_broker.encoder.CONTENT_TYPE,
            topic=topic,
            data=data,
            source=self.name,
            **kwargs,
        )
        return await _broker.publish(message)

    @property
    def consumers(self):
        return self.consumer_group.consumers

    async def publish(
        self, message: CloudEvent, broker: str = "default", **kwargs
    ) -> Any:
        if not message.source:
            message.source = self.name
        broker_ = self._brokers[broker]
        return await broker_.publish(message, **kwargs)

    async def publish_to_multiple(
        self, message: CloudEvent, brokers: tuple[str], **kwargs
    ) -> None:
        async with anyio.create_task_group() as tg:
            for broker in brokers:
                fn = functools.partial(self.publish, message, broker, **kwargs)
                tg.start_soon(fn)

    def publish_sync(self, message: CloudEvent, **kwargs) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.publish(message, **kwargs))

    async def connect_all(self) -> None:
        for broker in self._brokers.values():
            await broker.connect()
            await broker.dispatch_before("service_start", self)

    async def disconnect_all(self) -> None:
        self.logger.info("Disconnecting all brokers")
        for broker in self._brokers.values():
            await broker.dispatch_before("service_stop", self)
            await broker.disconnect()
            await broker.dispatch_after("service_stop", self)

    async def start(self, scope: CancelScope | None = None) -> None:
        self.logger.info(f"Starting service {self.name}...")
        await self.connect_all()
        try:
            async with anyio.create_task_group() as tg:
                for consumer in self.consumers.values():
                    self.logger.info(f"Starting consumer {consumer.name}")
                    for broker_name in consumer.brokers:
                        broker = self._brokers[broker_name]
                        tg.start_soon(broker.start_consumer, self, consumer)
                for broker in self.brokers:
                    await broker.dispatch_after("service_start", self)
        finally:
            if scope is not None:
                scope.cancel()

    async def stop(self) -> None:
        self.logger.info(f"Stopping service {self.name}")
        await self.disconnect_all()

    def get_service_runner(self, enable_signal_handler: bool = True):
        from .runner import ServiceRunner

        return ServiceRunner(self, enable_signal_handler=enable_signal_handler)

    async def run(self, enable_signal_handler: bool = True) -> None:
        runner = self.get_service_runner(enable_signal_handler=enable_signal_handler)
        await runner.run()

    def run_sync(self, enable_signal_handler: bool = True, **options):
        runner = self.get_service_runner(enable_signal_handler=enable_signal_handler)
        anyio.run(runner.run, **options)
