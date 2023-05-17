import asyncio

from pydantic import BaseModel

from eventiq import CloudEvent, Middleware, Service
from eventiq.asyncapi.models import PublishInfo
from eventiq.backends.nats.broker import JetStreamBroker

broker = JetStreamBroker(url="nats://localhost:4222")


class MyData(BaseModel):
    """Main data for service"""

    counter: int
    info: str


# @publishes("test.topic.{param}.*")
class MyEvent(CloudEvent[MyData]):
    """Some custom event"""


service = Service(
    name="example-service",
    version="1.0",
    broker=broker,
    publish_info=[PublishInfo.s(MyEvent, topic="test.topic.{param}.*", tags=["tag2"])],
    tags_metadata=[{"name": "tag1", "description": "Some tag 1"}],
)


class SendMessageMiddleware(Middleware):
    async def after_service_start(self, broker, service: Service):
        self.logger.info(f"After service start, running with {broker}")
        await asyncio.sleep(5)
        for i in range(100):
            await broker.publish(
                MyEvent(
                    topic="test.topic", data=MyData(**{"counter": i, "info": "default"})
                )
            )
        self.logger.info("Published event(s)")


broker.add_middleware(SendMessageMiddleware())


@service.subscribe("test.topic.{param}.*", tags=["tag1"])
async def example_run(message: MyEvent):
    """Consumer for processing MyEvent(s)"""
    print(f"Received Message {message.id} with data: {message.data}")
