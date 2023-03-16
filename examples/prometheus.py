import asyncio
import logging

from eventiq import CloudEvent, Middleware, Service
from eventiq.backends.nats.broker import JetStreamBroker
from eventiq.middlewares import PrometheusMiddleware, RetryMiddleware

broker = JetStreamBroker(url="nats://localhost:4222")

service = Service(name="example-service", broker=broker)

logger = logging.getLogger("consumer-logger")


class SendMessageMiddleware(Middleware):
    async def after_service_start(self, broker, service: Service):
        self.logger.info(f"After service start, running with {broker}")
        await asyncio.sleep(5)
        for i in range(3):
            await service.publish("test.topic", data={"counter": i})
        self.logger.info("Published event(s)")


broker.add_middlewares(
    [SendMessageMiddleware(), RetryMiddleware(), PrometheusMiddleware(run_server=True)]
)


@service.subscribe("test.topic", prefetch_count=10)
async def prometheus_consumer(message: CloudEvent):
    logger.info(f"Received Message {message.id} with data: {message.data}")
