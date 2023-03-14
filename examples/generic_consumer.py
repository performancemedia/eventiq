from eventiq import CloudEvent, GenericConsumer, Service
from eventiq.backends.stub import StubBroker
from eventiq.types import T

broker = StubBroker()

service = Service(name="example-service", broker=broker)


@service.subscribe("example.topic")
class MyConsumer(GenericConsumer[CloudEvent]):
    # optionally replace `CloudEvent` with more specific class
    name = "example_consumer"

    async def process(
        self, message: T
    ):  # `T` is bound to generic type var, so here T == CloudEvent
        print(message)
