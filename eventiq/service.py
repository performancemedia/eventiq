from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable

from .consumer import Consumer, ConsumerGroup, ForwardResponse
from .defaults import DEFAULT_CONSUMER_TIME_LIMIT
from .logger import LoggerMixin
from .models import CloudEvent
from .settings import ServiceSettings
from .utils import generate_instance_id

if TYPE_CHECKING:
    from .broker import Broker
    from .types import TagMeta


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
    ):
        self.broker = broker
        self.name = name
        self.title = title or name.title()
        self.version = version
        self.description = description
        self.tags_metadata = tags_metadata or []
        self.id = (instance_id_generator or generate_instance_id)()
        self.consumer_group = ConsumerGroup()
        # TODO: task gathering?
        self._tasks: list[asyncio.Task] = []

    def subscribe(
        self,
        topic: str,
        *,
        name: str | None = None,
        timeout: int = DEFAULT_CONSUMER_TIME_LIMIT,
        dynamic: bool = False,
        forward_response: ForwardResponse | None = None,
        **options,
    ):
        return self.consumer_group.subscribe(
            topic=topic,
            name=name,
            timeout=timeout,
            dynamic=dynamic,
            forward_response=forward_response,
            **options,
        )

    def add_consumer(self, consumer: Consumer):
        self.consumer_group.add_consumer(consumer)

    def add_consumer_group(self, consumer_group: ConsumerGroup) -> None:
        self.consumer_group.add_consumer_group(consumer_group)

    async def publish(
        self,
        topic: str,
        data: Any | None = None,
        type_: type[CloudEvent] | str = "CloudEvent",
        **kwargs,
    ):
        kwargs.setdefault("source", self.name)
        return await self.broker.publish(topic, data, type_, **kwargs)

    @property
    def consumers(self):
        return self.consumer_group.consumers

    async def publish_event(self, message: CloudEvent, **kwargs):
        if not message.source:
            message.set_source(self.name)
        return await self.broker.publish_event(message, **kwargs)

    async def start(self):
        await self.broker.dispatch_before("service_start", self)
        await self.broker.connect()
        for consumer in self.consumers.values():
            asyncio.create_task(self.broker.start_consumer(self, consumer))
        await self.broker.dispatch_after("service_start", self)

    async def stop(self, *args, **kwargs):
        await self.broker.dispatch_before("service_stop", self)
        await self.broker.disconnect()
        await self.broker.dispatch_after("service_stop", self)

    def run(self, *args, **kwargs):
        from .runner import ServiceRunner

        runner = ServiceRunner([self])
        runner.run(*args, **kwargs)

    @classmethod
    def from_settings(cls, settings: ServiceSettings, **kwargs: Any) -> Service:
        kw = settings.dict(exclude={"broker_settings"})
        kw.update(**kwargs)
        broker = Broker.from_settings(settings.broker_settings)
        return cls(broker=broker, **kw)

    @classmethod
    def from_env(cls, **kwargs: Any) -> Service:
        return cls.from_settings(ServiceSettings(), **kwargs)
