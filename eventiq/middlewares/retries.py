from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable

from eventiq.exceptions import Retry
from eventiq.middleware import Middleware
from eventiq.utils.datetime import utc_now

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer, Service


class RetryMiddleware(Middleware):
    """
    Retry Message Middleware
    """

    def __init__(
        self,
        backoff: int = 2,
        max_age: int = 3600,
        retry_when: Callable[[int, Exception], Awaitable[bool]] | None = None,
        throws: type[Exception] | tuple[type[Exception]] | None = None,
    ):
        self.backoff = backoff
        self.max_age = max_age
        self.retry_when = retry_when
        self.throws = throws

    async def after_process_message(
        self,
        broker: Broker,
        service: Service,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ):

        if exc is None:
            return
        throws = consumer.options.get("throws")
        if throws and isinstance(exc, throws):
            return

        retry_when = consumer.options.get("retry_when", self.retry_when)
        message_age = (utc_now() - message.time).seconds
        max_age = consumer.options.get("max_age", self.max_age)
        if (
            callable(retry_when)
            and not await retry_when(message_age, exc)
            or retry_when is None
            and message_age >= max_age
        ):
            self.logger.error(f"Retry limit exceeded for message {message.id}.")
            self.logger.exception("Original exception:", exc_info=exc)
            await broker.ack(service, consumer, message.raw)
            return

        if isinstance(exc, Retry) and exc.delay is not None:
            delay = exc.delay
        else:
            delay = consumer.options.get("backoff", self.backoff) * message_age

        self.logger.info("Retrying message %d seconds.", delay)
        await broker.nack(service, consumer, message.raw, delay)
