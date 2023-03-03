import asyncio

from eventiq import CloudEvent, Middleware, Service
from eventiq.backends.stub import StubBroker


class SendMessageMiddleware(Middleware):
    async def after_service_start(self, broker, service: Service):
        print(f"After service start, running with {broker}")
        await asyncio.sleep(5)
        for i in range(100):
            await service.publish("test.topic", data={"counter": i})
        print("Published event(s)")


broker = StubBroker(middlewares=[SendMessageMiddleware()])

service = Service(name="example-service", broker=broker)


@service.subscribe("test.topic")
async def example_run(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")


if __name__ == "__main__":
    service.run()
