from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping

from eventiq.exceptions import Retry
from eventiq.logger import LoggerMixin
from eventiq.middleware import Middleware

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer, Service


class RetryStrategy(LoggerMixin):
    def __init__(
        self,
        backoff: int = 2,
        throws: type[Exception] | tuple[type[Exception]] | None = None,
    ):
        self.backoff = backoff
        self.throws = throws

    def set_delay(self, message: CloudEvent, exc: Exception):
        delay = getattr(exc, "delay", None) or self.backoff * message.age.seconds
        message.raw.delay = delay
        self.logger.info("Will retry message %d seconds.", delay)

    def fail(self, message: CloudEvent, exc: Exception):
        message.fail()
        self.logger.error(f"Retry limit exceeded for message {message.id}.")
        self.logger.exception("Original exception:", exc_info=exc)

    async def maybe_retry(self, message: CloudEvent, exc: Exception):
        if self.throws and isinstance(exc, self.throws):
            message.fail()
        else:
            self.set_delay(message, exc)


class MaxAge(RetryStrategy):
    def __init__(
        self, max_age: timedelta | dict[str, Any] = timedelta(seconds=60), **extra
    ):
        super().__init__(**extra)
        if isinstance(max_age, Mapping):
            max_age = timedelta(**max_age)
        self.max_age: timedelta = max_age

    async def maybe_retry(self, message: CloudEvent, exc: Exception):
        if message.age <= self.max_age:
            await super().maybe_retry(message, exc)
        else:
            self.fail(message, exc)


class MaxRetries(RetryStrategy):
    def __init__(self, max_retries: int = 3, **extra):
        super().__init__(**extra)
        self.max_retries = max_retries

    async def maybe_retry(self, message: CloudEvent, exc: Exception):
        retries = getattr(
            message.raw, "_num_delivered", message.age.seconds
        )  # age used when num delivered is not supported
        if retries <= self.max_retries:
            await super().maybe_retry(message, exc)
        else:
            self.fail(message, exc)


class RetryWhen(RetryStrategy):
    def __init__(
        self, retry_when: Callable[[CloudEvent, Exception], Awaitable[bool]], **extra
    ):
        super().__init__(**extra)
        self.retry_when = retry_when

    async def maybe_retry(
        self,
        message: CloudEvent,
        exc: Exception,
    ):
        if await self.retry_when(message, exc):
            await super().maybe_retry(message, exc)
        else:
            self.fail(message, exc)


class RetryMiddleware(Middleware):
    """
    Retry Message Middleware.
    Supported retry strategies:
    - `MaxAge` (default) - retry with exponential backoff up to max_age
    - `MaxRetries` - retry up to N times (currently supported only by nats)
    - `RetryWhen` - provide custom callable to determine weather message should be retried
    """

    def __init__(self, default_retry_strategy: RetryStrategy | None = None):
        self.default_retry_strategy = default_retry_strategy or MaxAge(
            max_age=timedelta(hours=1)
        )

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

        if isinstance(exc, Retry):
            message.raw.delay = exc.delay
            return

        retry_strategy: RetryStrategy = consumer.options.get(
            "retry_strategy", self.default_retry_strategy
        )
        if retry_strategy is None:
            return

        await retry_strategy.maybe_retry(message, exc)
