from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from eventiq.broker import Broker
from eventiq.middleware import Middleware

if TYPE_CHECKING:
    from eventiq import CloudEvent, Consumer, Service
    from eventiq.message import Message
    from eventiq.types import Encoder


@dataclass
class StubMessage:
    data: bytes
    queue: asyncio.Queue


class StubBroker(Broker[StubMessage]):
    """This is in-memory implementation of a broker class, mainly designed for testing."""

    protocol = "in-memory"

    def __init__(
        self,
        *,
        encoder: Encoder | None = None,
        middlewares: list[Middleware] | None = None,
        **options: Any,
    ) -> None:
        super().__init__(encoder=encoder, middlewares=middlewares, **options)
        self.topics: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._stopped = False

    def parse_incoming_message(self, message: StubMessage) -> Any:
        return self.encoder.decode(message.data)

    async def _disconnect(self) -> None:
        self._stopped = True

    async def _start_consumer(self, service: Service, consumer: Consumer):
        queue = self.topics[consumer.topic]
        handler = self.get_handler(service, consumer)
        while not self._stopped:
            message = await queue.get()
            await handler(message)

    async def _connect(self) -> None:
        pass

    async def _publish(self, message: CloudEvent, **_) -> None:
        queue = self.topics[message.topic]
        data = self.encoder.encode(message.dict())
        msg = StubMessage(data=data, queue=queue)
        await queue.put(msg)

    async def _ack(self, message: Message) -> None:
        message.queue.task_done()

    async def _nack(self, message: Message) -> None:
        await message.queue.put(message)

    def is_connected(self) -> bool:
        return True
