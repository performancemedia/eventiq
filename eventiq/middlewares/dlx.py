from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventiq.exceptions import Fail
from eventiq.middleware import Middleware

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer, Service


class DeadLetterQueueMiddleware(Middleware):
    def __init__(self, topic: str = "dlx", type_: str = "MessageFailedEvent", **kwargs):
        self.topic = topic
        self.type_ = type_
        self.kwargs = kwargs

    async def after_process_message(
        self,
        broker: Broker,
        service: Service,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ) -> None:
        if exc and isinstance(exc, Fail) or message.raw.failed:
            topic = self.topic.format(
                message=message, consumer=consumer, service=service, broker=broker
            )
            await service.send(topic, self.type_, message, **self.kwargs)
