from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.propagate import extract, inject
from opentelemetry.propagators.textmap import Getter, Setter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.trace import MessagingOperationValues, SpanAttributes
from opentelemetry.trace import SpanKind, StatusCode

from ..middleware import Middleware
from ..models import CloudEvent
from ..types import ID

if TYPE_CHECKING:
    from eventiq import Broker, Consumer, Service


class EventiqGetter(Getter[CloudEvent]):
    def get(self, carrier: CloudEvent, key: str) -> list[str] | None:
        val = carrier.trace_ctx.get(key, None)
        if val is None:
            return None
        if isinstance(val, typing.Iterable) and not isinstance(val, str):
            return list(val)
        return [val]

    def keys(self, carrier: CloudEvent) -> list[str]:
        return list(carrier.trace_ctx.keys())


class EventiqSetter(Setter[CloudEvent]):
    def set(self, carrier: CloudEvent, key: str, value: str) -> None:
        carrier.trace_ctx[key] = value


eventiq_getter = EventiqGetter()
eventiq_setter = EventiqSetter()


class OpenTelemetryMiddleware(Middleware):
    def __init__(self, provider: TracerProvider | None = None):
        if provider is None:
            provider = TracerProvider()
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)

            trace.set_tracer_provider(provider)

        self.tracer = provider.get_tracer("eventiq")
        self.process_span_registry: dict[
            tuple[str, str, ID], tuple[Span, typing.ContextManager[Span]]
        ] = {}
        self.publish_span_registry: dict[
            ID, tuple[Span, typing.ContextManager[Span]]
        ] = {}

    @classmethod
    def from_kwargs(cls, endpoint: str, name: str):
        resource = Resource(attributes={"service.name": name})
        tracer = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer)
        LoggingInstrumentor().instrument()
        tracer.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        return cls(tracer)

    async def before_process_message(
        self, broker: Broker, service: Service, consumer: Consumer, message: CloudEvent
    ) -> None:
        """Start span"""

        trace_ctx = extract(message, getter=eventiq_getter)
        span = self.tracer.start_span(
            name=f"{service.name}.{consumer.name} receive",
            kind=SpanKind.CONSUMER,
            context=trace_ctx,
            attributes={
                SpanAttributes.MESSAGING_OPERATION: MessagingOperationValues.PROCESS.value,
                SpanAttributes.MESSAGING_MESSAGE_ID: str(message.id),
            },
        )
        activation = trace.use_span(span, end_on_exit=True)
        activation.__enter__()
        self.process_span_registry[(service.name, consumer.name, str(message.id))] = (
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
        """End span"""
        key = (service.name, consumer.name, str(message.id))
        span, activation = self.process_span_registry.pop(key, (None, None))
        if span is None or activation is None:
            self.logger.warning(f"Span not found, {self.process_span_registry}")
            return

        if span.is_recording():
            status = (StatusCode.ERROR, str(exc)) if exc else (StatusCode.OK,)
            span.set_status(*status)

        activation.__exit__(None, None, None)

    async def before_publish(
        self, broker: Broker, message: CloudEvent, **kwargs
    ) -> None:
        """Inject context"""
        source = message.source or "(anonymous)"
        span = self.tracer.start_span(f"{source} publish", kind=SpanKind.PRODUCER)

        activation = trace.use_span(span, end_on_exit=True)
        activation.__enter__()
        self.publish_span_registry[message.id] = (span, activation)
        inject(message, setter=eventiq_setter)

    async def after_publish(
        self, broker: Broker, message: CloudEvent, **kwargs
    ) -> None:
        _, activation = self.publish_span_registry.pop(message.id, (None, None))

        if activation is not None:
            activation.__exit__(None, None, None)
