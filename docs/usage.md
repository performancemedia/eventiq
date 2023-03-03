## Basic Usage

```Python
import asyncio
from eventiq import Service, Middleware, CloudEvent
from eventiq.backends.nats import JetStreamBroker


broker = JetStreamBroker(url="nats://localhost:4222")

service = Service(name="example-service", broker=broker)


class SendMessageMiddleware(Middleware):
    async def after_service_start(self, broker: JetStreamBroker, service: Service):
        print(f"After service start, running with {broker}")
        await asyncio.sleep(10)
        for i in range(100):
            await service.publish("test.topic", data={"counter": i})
        print("Published event(s)")


broker.add_middleware(SendMessageMiddleware())


@service.subscribe("test.topic")
async def example_run(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")
```

Run with

```shell
eventiq app:service
```

## Web integration (FastAPI)



## Testing

`StubBroker` class is provided as in memory replacement for running unit tests

```python
import os


def get_broker(**kwargs):
    if os.getenv('ENV') == 'TEST':
        from eventiq.backends.stub import StubBroker
        return StubBroker()
    else:
        from eventiq.backends.rabbitmq import RabbitmqBroker
        return RabbitmqBroker(**kwargs)

broker = get_broker()

```

Furthermore, subscribers are just regular python coroutines, so it's possible to test
them simply by invocation

```python

# main.py
@service.subscribe(...)
async def my_subscriber(message: CloudEvent):
    return 42

# tests.py
from main import my_subscriber

async def test_my_subscriber():
    result = await my_subscriber(None)
    assert result == 42

```

## Configuration

*Explicit is better than implicit.*

eventiq package does not provide any 'magic' configuration management
or dependency injection providers. You have to create `broker`, `service`, and `middlewares`
instances by hand and provide all the parameters. However, it's up to user which approach
to use: config file (yaml/ini), pydantic settings management, constants in code, dependency
injector library etc.