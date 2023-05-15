import asyncio
import logging
import random

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
    attributes={"service.name": service.name, "service.version": service.version}
)


tracer = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer)
# Make sure to install:
# opentelemetry-exporter-otlp
# opentelemetry-instrumentation-logging
LoggingInstrumentor().instrument()

tracer.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://tempo:4317"))
)


class SendMessageMiddleware(Middleware):
    async def after_service_start(self, broker, service: Service):
        self.logger.info(f"After service start, running with {broker}")
        await asyncio.sleep(5)
        for i in range(3):
            await service.send("test.topic", data={"counter": i})
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
async def consumer_1(message: CloudEvent, **_):
    logger.info(f"Received Message {message.id} with data: {message.data}")
    await asyncio.sleep(0.4)
    await service.send("test.topic2", data=message.data)


@service.subscribe("test.topic", retry_strategy=MaxAge(max_age={"seconds": 60}))
async def consumer_2(message: CloudEvent, **_):
    await asyncio.sleep(0.2)
    logger.info(f"Received Message {message.id} with data: {message.data}")


@service.subscribe("test.topic2")
async def consumer_3(message: CloudEvent, **_):
    await asyncio.sleep(0.2)
    logger.info(f"Received Message {message.id} with data: {message.data}")
    await service.send("test.topic3", data=message.data)


@service.subscribe("test.topic3")
async def consumer_4(message: CloudEvent, **_):
    await asyncio.sleep(0.2)
    logger.info(f"Received Message {message.id} with data: {message.data}")
    if random.randint(1, 3) == 2:  # nosec
        await service.send("test.topic", data=message.data)
