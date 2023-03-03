# Consumers

The framework allows to add consumers in two ways:

1. Using decorator `Service.subscribe`

```python
from eventiq import Service, CloudEvent

service = Service(...) # options

# all the options passed to subscribe, are used to initialize consumer class (__init__)
@service.subscribe("example_topic") 
async def my_consumer(message: CloudEvent):
    print(f"Received message {message}")
```

This will create `FnConsumer` instance under the hood. It's also possible to use
regular functions (without `async`) which will be run in the thread pool.

2. By subclassing `GenericConsumer`

```python
from eventiq import GenericConsumer, CloudEvent, Service

service = Service(...) # options

@service.subscribe("example_topic")
class MyConsumer(GenericConsumer[CloudEvent]):
    name = "my_consumer"
    x = 10

    async def process(self, message: CloudEvent):
        print(f"Consumer {self.name}.{self.x} received message  {message}")
```
Subclassing `Consumer` allows you to specify the base class and/or use mixins with shared
functionality.

## Automatic response forwarding
If `ForwardResponse` option is set for consumer, then returned value is
automatically published to the broker.

## Reference
::: eventiq.consumer.Consumer
    handler: python
    options:
      members:
        - __init__
        - process
      show_root_heading: true
      show_source: false

::: eventiq.consumer.GenericConsumer
    handler: python
    options:
      members:
        - __init__
        - process
      show_root_heading: true
      show_source: false