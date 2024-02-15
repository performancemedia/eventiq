import asyncio
from typing import Any, Literal

from pydantic import BaseModel

from eventiq import CloudEvent, Middleware, Service
from eventiq.backends.nats import JetStreamBroker
from eventiq.middlewares.retries import RetryMiddleware


class TestParams(BaseModel):
    action: Literal["create", "update", "delete"]
    region: str


class SomeEvent(CloudEvent[Any], topic="events.{region}.users.{action}"):
    some_attribute: str = "some value"


class SendMessageMiddleware(Middleware):
    async def after_service_start(self, broker, service: Service):
        print(f"After service start, running with {broker}")
        await asyncio.sleep(5)
        for i in range(100):
            await service.send("test.topic", data={"counter": i})

        print("Published event(s)")


broker = JetStreamBroker(
    url="nats://localhost:4222",
    middlewares=[SendMessageMiddleware(), RetryMiddleware()],
)

service = Service(name="example-service", broker=broker)


@service.subscribe("test.topic")
async def example_run(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")
    await asyncio.sleep(5)
