from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from eventiq.broker import Broker
from eventiq.middleware import Middleware
from eventiq.settings import BrokerSettings

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Encoder, Service
    from eventiq.message import Message
    from eventiq.types import ServerInfo


@dataclass
class StubMessage:
    data: bytes
    queue: asyncio.Queue
    event: asyncio.Event
    headers: dict[str, str] = field(default_factory=dict)


class StubSettings(BrokerSettings):
    wait_on_publish: bool = True


class StubBroker(Broker[StubMessage, dict[str, asyncio.Event]]):
    """This is in-memory implementation of a broker class, mainly designed for testing."""

    Settings = StubSettings

    protocol = "in-memory"

    WILDCARD_ONE = r"\w+"
    WILDCARD_MANY = "*"

    def __init__(
        self,
        *,
        encoder: Encoder | None = None,
        middlewares: list[Middleware] | None = None,
        wait_on_publish: bool = True,
        **options: Any,
    ) -> None:
        super().__init__(encoder=encoder, middlewares=middlewares, **options)
        self.topics: dict[str, asyncio.Queue[StubMessage]] = defaultdict(
            lambda: asyncio.Queue(maxsize=100)
        )
        self._stopped = False
        self.wait_on_publish = wait_on_publish

    def get_info(self) -> ServerInfo:
        return {"host": "localhost", "protocol": "memory"}

    def parse_incoming_message(self, message: StubMessage, encoder: Encoder) -> Any:
        return encoder.decode(message.data)

    async def _start_consumer(self, service: Service, consumer: Consumer):
        queue = self.topics[self.format_topic(consumer.topic)]
        handler = self.get_handler(service, consumer)
        while self._connected:
            message = await queue.get()
            await handler(message)

    async def _connect(self) -> None:
        pass

    async def _disconnect(self) -> None:
        pass

    async def _publish(self, message: CloudEvent, **kwargs) -> dict[str, asyncio.Event]:
        data = self.encoder.encode(message.model_dump())
        headers = kwargs.get("headers", {})
        response = {}
        for topic, queue in self.topics.items():
            if re.fullmatch(topic, message.topic):
                event = asyncio.Event()
                msg = StubMessage(data=data, queue=queue, event=event, headers=headers)
                await queue.put(msg)
                response[topic] = event
                if self.wait_on_publish:
                    await event.wait()
        return response

    async def _ack(self, message: Message) -> None:
        message.queue.task_done()
        message.event.set()

    async def _nack(self, message: Message) -> None:
        await message.queue.put(message)

    def is_connected(self) -> bool:  # type: ignore[override]
        return self._connected
