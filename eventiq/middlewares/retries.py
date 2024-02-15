from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Generic

from eventiq.exceptions import Fail, Retry
from eventiq.logger import LoggerMixin
from eventiq.middleware import Middleware, T
from eventiq.utils import utc_now

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer, Service

from typing_extensions import ParamSpec

P = ParamSpec("P")
R = Callable[["CloudEvent", Exception], int]
DelayGenerator = Callable[[P.args, P.kwargs], R]


def expo(factor: int = 1) -> R:
    def _expo(message: CloudEvent, _: Exception) -> int:
        return factor * message.age.seconds

    return _expo


def constant(interval: int = 30) -> R:
    def _constant(*_) -> int:
        return interval

    return _constant


class RetryStrategy(Generic[P], LoggerMixin):
    def __init__(
        self,
        throws: tuple[type[Exception], ...] = (),
        delay_generator: DelayGenerator[P] | None = None,
        min_delay: int = 2,
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        if Fail not in throws:
            throws = (*throws, Fail)
        self.throws = throws
        self.min_delay = min_delay
        self.delay_generator = (
            delay_generator(*args, **kwargs) if delay_generator else expo()
        )

    def set_delay(self, message: CloudEvent, exc: Exception):
        delay = getattr(exc, "delay", None)
        if delay is None:
            delay = self.delay_generator(message, exc)
        delay = max(delay, self.min_delay)
        message.set_delay(delay)
        self.logger.info(f"Will retry message {message.id} in %d seconds.", delay)

    def fail(self, message: CloudEvent, exc: Exception):
        message.fail()
        self.logger.error(f"Retry limit exceeded for message {message.id}.")
        self.logger.exception("Original exception:", exc_info=exc)

    def maybe_retry(self, message: CloudEvent, exc: Exception):
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

    def maybe_retry(self, message: CloudEvent, exc: Exception):
        if message.age <= self.max_age:
            super().maybe_retry(message, exc)
        else:
            self.fail(message, exc)


class MaxRetries(RetryStrategy):
    def __init__(self, max_retries: int = 3, **extra):
        super().__init__(**extra)
        self.max_retries = max_retries

    def maybe_retry(self, message: CloudEvent, exc: Exception):
        retries = getattr(message.raw, "num_delivered", None)
        if retries is None:
            self.logger.warning(
                "Retries property not found in message, backing off to message.age.seconds"
            )
            retries = message.age.seconds
        if retries <= self.max_retries:
            super().maybe_retry(message, exc)
        else:
            self.fail(message, exc)


class RetryWhen(RetryStrategy):
    def __init__(self, retry_when: Callable[[CloudEvent, Exception], bool], **extra):
        super().__init__(**extra)
        self.retry_when = retry_when

    def maybe_retry(
        self,
        message: CloudEvent,
        exc: Exception,
    ):
        if self.retry_when(message, exc):
            super().maybe_retry(message, exc)
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

        retry_strategy = consumer.retry_strategy or self.default_retry_strategy
        if retry_strategy is None:
            return

        retry_strategy.maybe_retry(message, exc)

    async def before_publish(self, broker: T, message: CloudEvent, **kwargs) -> None:
        delay = kwargs.get("delay")
        if delay is not None:
            not_before = (utc_now() + timedelta(seconds=message.delay)).isoformat()
            message.set_header("x-not-before", not_before)

    async def before_process_message(
        self, broker: T, service: Service, consumer: Consumer, message: CloudEvent
    ) -> None:
        """Broker agnostic implementation of not-before header."""
        not_before_header = message.headers.get("x-not-before")
        if not_before_header is None:
            return
        try:
            not_before = datetime.fromisoformat(not_before_header)
        except (ValueError, TypeError):
            self.logger.warning(
                f"Error parsing 'x-not-before' header: {not_before_header}"
            )
            return
        delay = int((not_before - utc_now()).total_seconds()) + 1
        if delay > 0:
            self.logger.info(
                f"Message {message.id} not ready for processing, delaying for {delay}."
            )
            raise Retry(delay=delay)
