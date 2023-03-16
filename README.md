<p align="center">
<img src="https://performancemedia.github.io/eventiq/assets/logo.svg" style="width: 250px">

</p>
<p align="center">
<em>Cloud native framework for building event driven applications in Python</em>
</p>

![Tests](https://github.com/performancemedia/eventiq/workflows/Test/badge.svg)
![Build](https://github.com/performancemedia/eventiq/workflows/Publish/badge.svg)
![License](https://img.shields.io/github/license/performancemedia/eventiq)
![Python](https://img.shields.io/pypi/pyversions/eventiq)
![Format](https://img.shields.io/pypi/format/eventiq)
![PyPi](https://img.shields.io/pypi/v/eventiq)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

*Note: This package is under active development and is not recommended for production use*

|Version|0.1.1|
|Documentation|
|--|---|---|

---
Version: 0.1.3

Documentation: https://performancemedia.github.io/eventiq/

Repository: https://github.com/performancemedia/eventiq

---
## About

The package utilizes `pydantic`, `async_timeout` and `python-json-logger` as the only required dependencies.
For messages [Cloud Events](https://cloudevents.io/) format is used.
Service can be run as standalone processes, or included into starlette (e.g. FastAPI) applications.

## Installation

```shell
pip install eventiq
```

## Multiple broker support (in progress)

- Stub (in memory using `asyncio.Queue` for PoC, local development and testing)
- NATS (with JetStream)
- Redis Pub/Sub
- Kafka
- Rabbitmq
- Google Cloud PubSub
- And more comming

## Optional Dependencies
  - `cli` - `typer` and `aiorun`
  - broker of choice: `nats`, `kafka`, `rabbitmq`, `redis`, `pubsub`
  - custom message serializers: `msgpack`, `orjson`
  - `prometheus` - Metric exposure via `PrometheusMiddleware`

## Motivation

- [Celery](https://docs.celeryq.dev/en/stable/getting-started/introduction.html)
- [Dramatiq](https://dramatiq.io/)
- [Huey](https://huey.readthedocs.io/en/latest/)
- [arq](https://arq-docs.helpmanual.io/)

However, those libraries don't provide a pub/sub pattern, useful for creating
event driven and loosely coupled systems. Furthermore, the majority of those libraries
do not support `asyncio`. This is why this project was born.

## Basic usage


```python
import asyncio
from eventiq import Service, CloudEvent, Middleware
from eventiq.backends.nats.broker import JetStreamBroker


class SendMessageMiddleware(Middleware):
    async def after_broker_connect(self, broker: "Broker") -> None:
        print(f"After service start, running with {broker}")
        await asyncio.sleep(10)
        for i in range(100):
            await broker.publish("test.topic", data={"counter": i})
        print("Published event(s)")

broker = JetStreamBroker(url="nats://localhost:4222")
broker.add_middleware(SendMessageMiddleware())

service = Service(name="example-service", broker=broker)

@service.subscribe("test.topic")
async def example_run(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")


if __name__ == "__main__":
    service.run()

```


## Scaling

Each message is load-balanced (depending on broker) between all service instances with the same `name`.
To scale number of processes you can use containers (docker/k8s), [supervisor](http://supervisord.org/),
or web server like gunicorn.


## TODOS:
- More tests
  - Integration tests with docker-compose and all backends
- Docs + tutorials
- [OpenTelemetry](https://opentelemetry.io/) Middleware (?)