from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Callable

import anyio

from .asyncapi import PUBLISH_REGISTRY
from .consumer import Consumer, ConsumerGroup
from .logger import LoggerMixin
from .models import CloudEvent
from .settings import ServiceSettings
from .utils import generate_instance_id

if TYPE_CHECKING:
    from eventiq import Broker

    from .asyncapi import PublishInfo
    from .middlewares.retries import RetryStrategy
    from .types import Encoder, TagMeta, Tags


class AbstractService(ABC):
    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError


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
        self._brokers = {}
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
        self._task = None
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
        timeout: int | None = None,
        dynamic: bool = False,
        forward_response: bool = False,
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
            forward_response=forward_response,
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
    ) -> None:
        if not message.source:
            message.source = self.name
        broker_ = self._brokers[broker]
        await broker_.publish(message, **kwargs)

    async def publish_to_multiple(
        self, message: CloudEvent, brokers: tuple[str], **kwargs
    ) -> None:
        for broker in brokers:
            await self.publish(message, broker, **kwargs)

    def publish_sync(self, message: CloudEvent, **kwargs) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.publish(message, **kwargs))

    async def connect_all(self) -> None:
        for broker in self._brokers.values():
            await broker.connect()
            await broker.dispatch_before("service_start", self)

    async def disconnect_all(self) -> None:
        for broker in self._brokers.values():
            await broker.dispatch_before("service_stop", self)
            await broker.disconnect()
            await broker.dispatch_after("service_stop", self)

    def start_soon(self):
        self._task = asyncio.create_task(self.start())

    async def start(self) -> None:
        self.logger.info(f"Starting service {self.name}...")
        await self.connect_all()

        async with anyio.create_task_group() as tg:
            for consumer in self.consumers.values():
                self.logger.info(f"Starting consumer {consumer.name}")
                for broker_name in consumer.brokers:
                    broker = self._brokers[broker_name]
                    tg.start_soon(broker.start_consumer, self, consumer)
            for broker in self.brokers:
                await broker.dispatch_after("service_start", self)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.wait_for(self._task, timeout=15)
        await self.disconnect_all()

    async def run(self) -> None:
        from .runner import ServiceRunner

        runner = ServiceRunner(self)
        await runner.run()

    @classmethod
    def from_settings(cls, settings: ServiceSettings, **kwargs: Any) -> Service:
        return cls(**settings.model_dump(), **kwargs)

    @classmethod
    def from_env(cls, **kwargs: Any) -> Service:
        return cls.from_settings(ServiceSettings(), **kwargs)
