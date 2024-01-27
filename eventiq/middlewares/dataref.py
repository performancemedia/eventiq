from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from eventiq import Middleware

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer, Service


class DataRefStorage(Protocol):
    async def load(self, dataref: str) -> Any:
        ...

    async def save(self, dataref: str, data: Any) -> None:
        ...


class DataRefResolverMiddleware(Middleware):
    throws = ()

    def __init__(self, storage: DataRefStorage):
        self.storage = storage

    async def before_process_message(
        self, broker: Broker, service: Service, consumer: Consumer, message: CloudEvent
    ) -> None:
        if message.dataref and not message.data:
            message.data = await self.storage.load(message.dataref)

    async def before_publish(
        self, broker: Broker, message: CloudEvent, **kwargs
    ) -> None:
        if message.dataref and message.data:
            await self.storage.save(message.dataref, message.data)
            message.data = None
