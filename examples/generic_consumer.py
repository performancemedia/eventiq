from eventiq import CloudEvent, GenericConsumer, Service
from eventiq.backends.stub import StubBroker

broker = StubBroker()

service = Service(name="example-service", broker=broker)


@service.subscribe("example.topic")
class MyConsumer(GenericConsumer):
    name = "example_consumer"

    async def process(self, message: CloudEvent):
        print(f"Received {message}")
