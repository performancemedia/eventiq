from __future__ import annotations

from collections.abc import Iterable
from contextlib import AbstractContextManager as ContextManager
from itertools import chain
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.propagators.textmap import Getter, Setter
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind, StatusCode

from .._version import __version__
from ..exceptions import Retry, Skip
from ..middleware import Middleware
from ..models import CloudEvent

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import Span, TracerProvider

    from eventiq import Broker, Consumer, Service
    from eventiq.types import ID


class EventiqGetter(Getter[CloudEvent]):
    def get(self, carrier: CloudEvent, key: str) -> list[str] | None:
        val = carrier.tracecontext.get(key, None)
        if val is None:
            return None
        if isinstance(val, Iterable) and not isinstance(val, str):
            return list(val)
        return [val]

    def keys(self, carrier: CloudEvent) -> list[str]:
        return list(carrier.tracecontext.keys())


class EventiqSetter(Setter[CloudEvent]):
    def set(self, carrier: CloudEvent, key: str, value: str) -> None:
        carrier.tracecontext[key] = value


eventiq_getter = EventiqGetter()
eventiq_setter = EventiqSetter()


class OpenTelemetryMiddleware(Middleware):
    def __init__(
        self, provider: TracerProvider | None = None, record_exceptions: bool = True
    ):
        if provider is None:
            provider = trace.get_tracer_provider()
        self.record_exceptions = record_exceptions
        self.tracer = provider.get_tracer("eventiq", __version__)
        self.process_span_registry: dict[
            tuple[str, str, ID], tuple[Span, ContextManager[Span]]
        ] = {}
        self.publish_span_registry: dict[ID, tuple[Span, ContextManager[Span]]] = {}

    @staticmethod
    def _get_span_attributes(message: CloudEvent, broker: Broker | None = None):
        extra = broker.extra_message_span_attributes(message.raw) if broker else {}
        return {
            SpanAttributes.CLOUDEVENTS_EVENT_ID: str(message.id),
            SpanAttributes.CLOUDEVENTS_EVENT_SOURCE: message.source or "(anonymous)",
            SpanAttributes.CLOUDEVENTS_EVENT_TYPE: message.type or "CloudEvent",
            SpanAttributes.CLOUDEVENTS_EVENT_SUBJECT: message.topic,
            **{
                k: str(v)
                for k, v in chain(extra.items(), message.extra_span_attributes.items())
                if v is not None
            },
        }

    async def before_process_message(
        self, broker: Broker, service: Service, consumer: Consumer, message: CloudEvent
    ) -> None:
        trace_ctx = extract(message, getter=eventiq_getter)

        span = self.tracer.start_span(
            name=f"{consumer.name} receive",
            kind=SpanKind.CONSUMER,
            context=trace_ctx,
            attributes=self._get_span_attributes(message, broker),
        )
        activation = trace.use_span(span, end_on_exit=True)
        activation.__enter__()
        self.process_span_registry[(service.name, consumer.name, message.id)] = (
            span,
            activation,
        )

    async def after_process_message(
        self,
        broker: Broker,
        service: Service,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ) -> None:
        key = (service.name, consumer.name, message.id)
        span, activation = self.process_span_registry.pop(key, (None, None))
        if span is None or activation is None:
            self.logger.warning("No active span was found")
            return

        if span.is_recording():
            if exc:
                if isinstance(exc, (Retry, Skip)):
                    span.set_status(StatusCode.OK, description=str(exc))
                else:
                    if self.record_exceptions:
                        span.record_exception(exc)
                    span.set_status(StatusCode.ERROR, description=str(exc))

            else:
                if message.failed:
                    span.set_status(StatusCode.ERROR, description="Failed")
                else:
                    span.set_status(StatusCode.OK)

        activation.__exit__(None, None, None)

    async def before_publish(
        self, broker: Broker, message: CloudEvent, **kwargs
    ) -> None:
        source = message.source or "(anonymous)"

        span = self.tracer.start_span(
            f"{source} publish",
            kind=SpanKind.PRODUCER,
            attributes=self._get_span_attributes(message),
        )
        activation = trace.use_span(span, end_on_exit=True)
        activation.__enter__()
        self.publish_span_registry[message.id] = (span, activation)
        inject(message, setter=eventiq_setter)

    async def after_publish(
        self, broker: Broker, message: CloudEvent, **kwargs
    ) -> None:
        span, activation = self.publish_span_registry.pop(message.id, (None, None))
        if span and span.is_recording():
            span.set_status(StatusCode.OK)
        if activation is not None:
            activation.__exit__(None, None, None)
