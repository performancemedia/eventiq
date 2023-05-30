from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Sequence

import anyio

from .asyncapi.models import PublishInfo
from .asyncapi.registry import PUBLISH_REGISTRY
from .consumer import Consumer, ConsumerGroup, ForwardResponse
from .logger import LoggerMixin
from .models import CloudEvent
from .settings import DEFAULT_TIMEOUT, ServiceSettings
from .utils import generate_instance_id

if TYPE_CHECKING:
    from eventiq import Broker

    from .middlewares.retries import RetryStrategy
    from .types import TagMeta, Tags


class Service(LoggerMixin):
    """Logical group of consumers. Provides group (queue) name and handles versioning"""

    def __init__(
        self,
        name: str,
        broker: Broker,
        title: str | None = None,
        version: str = "0.1.0",
        description: str = "",
        tags_metadata: list[TagMeta] | None = None,
        instance_id_generator: Callable[[], str] | None = None,
        base_event_class: type[CloudEvent] = CloudEvent,
        publish_info: Sequence[PublishInfo] = (),
        **context: Any,
    ):
        self.broker = broker
        self.name = name
        self.title = title or name.title()
        self.version = version
        self.description = description
        self.tags_metadata = tags_metadata or []
        self.id = (instance_id_generator or generate_instance_id)()
        self.consumer_group = ConsumerGroup()
        self.context = context
        self.base_event_class = base_event_class
        for p in publish_info:
            PUBLISH_REGISTRY[p.event_type.__name__] = p

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
        **options: Any,
    ):
        return self.consumer_group.subscribe(
            topic=topic,
            name=name,
            timeout=timeout,
            dynamic=dynamic,
            forward_response=forward_response,
            tags=tags,
            retry_strategy=retry_strategy,
            store_results=store_results,
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
        **kwargs,
    ):
        if isinstance(type_, str):
            cls = self.base_event_class
            type_name = type_
        else:
            cls = type_
            type_name = type_.__name__

        message: CloudEvent = cls(
            content_type=self.broker.encoder.CONTENT_TYPE,
            type=type_name,
            topic=topic,
            data=data,
            source=self.name,
            **kwargs,
        )
        return await self.broker.publish(message)

    @property
    def consumers(self):
        return self.consumer_group.consumers

    async def publish(self, message: CloudEvent, **kwargs):
        if not message.source:
            message.set_source(self.name)
        return await self.broker.publish(message, **kwargs)

    async def start(self):
        self.logger.info(f"Starting service {self.name}")
        await self.broker.connect()
        await self.broker.dispatch_before("service_start", self)

        async with anyio.create_task_group() as tg:
            for consumer in self.consumers.values():
                self.logger.info(f"Starting consumer {consumer.name}")
                tg.start_soon(self.broker.start_consumer, self, consumer)
            await self.broker.dispatch_after("service_start", self)

    async def stop(self, *args, **kwargs):
        await self.broker.dispatch_before("service_stop", self)
        await self.broker.disconnect()
        await self.broker.dispatch_after("service_stop", self)

    async def run(self):
        from .runner import ServiceRunner

        runner = ServiceRunner([self])
        await runner.run()

    @classmethod
    def from_settings(cls, settings: ServiceSettings, **kwargs: Any) -> Service:
        return cls(**settings.dict(), **kwargs)

    @classmethod
    def from_env(cls, **kwargs: Any) -> Service:
        return cls.from_settings(ServiceSettings(), **kwargs)
