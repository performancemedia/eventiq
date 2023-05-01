import asyncio
import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from eventiq import CloudEvent, Middleware, Service
from eventiq.backends.nats.broker import JetStreamBroker
from eventiq.middlewares import PrometheusMiddleware, RetryMiddleware
from eventiq.middlewares.opentelemetry import OpenTelemetryMiddleware
from eventiq.middlewares.retries import MaxAge

broker = JetStreamBroker(url="nats://nats:4222")

service = Service(name="example-service", broker=broker)

logger = logging.getLogger("consumer-logger")

resource = Resource(
    attributes={"service.name": service.name}
)  # set the service name to show in traces

# set the tracer provider
tracer = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer)
LoggingInstrumentor().instrument()
# Use the OTLPSpanExporter to send traces to Tempo
tracer.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://tempo:4317"))
)


class SendMessageMiddleware(Middleware):
    async def after_service_start(self, broker, service: Service):
        self.logger.info(f"After service start, running with {broker}")
        await asyncio.sleep(5)
        for i in range(3):
            await service.publish("test.topic", data={"counter": i})
        self.logger.info("Published event(s)")


broker.add_middlewares(
    [
        SendMessageMiddleware(),
        RetryMiddleware(),
        PrometheusMiddleware(run_server=True),
        OpenTelemetryMiddleware(tracer),
    ]
)


@service.subscribe("test.topic", retry_strategy=MaxAge(max_age={"seconds": 60}))
async def consumer_1(message: CloudEvent):
    logger.info(f"Received Message {message.id} with data: {message.data}")
    await asyncio.sleep(0.4)


@service.subscribe("test.topic", retry_strategy=MaxAge(max_age={"seconds": 60}))
async def consumer_2(message: CloudEvent):
    await asyncio.sleep(0.2)
    logger.info(f"Received Message {message.id} with data: {message.data}")
