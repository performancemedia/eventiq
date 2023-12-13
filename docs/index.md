
<p align="center">
<img src="./assets/logo.svg" style="width: 250px">
</p>

## Welcome to eventiq documentation

![Tests](https://github.com/performancemedia/eventiq/workflows/CI/badge.svg)
![Build](https://github.com/performancemedia/eventiq/workflows/Publish/badge.svg)
![Python](https://img.shields.io/pypi/pyversions/eventiq)
![Format](https://img.shields.io/pypi/format/eventiq)
![PyPi](https://img.shields.io/pypi/v/eventiq?color=%2334D05)
![Mypy](https://img.shields.io/badge/mypy-checked-blue)
![License](https://img.shields.io/github/license/performancemedia/eventiq)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)

*Cloud native, event driven microservice framework for python*

*Note: This package is under active development and is not recommended for production usage*

---
Version: 0.1.23

Documentation: [https://performancemedia.github.io/eventiq/](https://performancemedia.github.io/eventiq/)

Repository: [https://github.com/performancemedia/eventiq](https://github.com/performancemedia/eventiq)

---
## About

The package utilizes `anyio` and `pydantic` as the only required dependencies.
For messages [Cloud Events](https://cloudevents.io/) format is used.
Service can be run as standalone processes, or included into starlette (e.g. FastAPI) applications.

## Installation

```shell
pip install eventiq
```

## Multiple brokers support

- Stub (in memory using `asyncio.Queue` for PoC, local development and testing)
- NATS (with JetStream)
- Redis Pub/Sub
- Kafka
- Rabbitmq
- Google Cloud PubSub
- *And more coming...*

## Optional Dependencies
  - `cli` - `typer` and `aiorun`
  - broker of choice: `nats`, `kafka`, `rabbitmq`, `redis`, `pubsub`
  - custom message serializers: `msgpack`, `orjson`
  - `prometheus` - Metric exposure via `PrometheusMiddleware`
  - `opentelemetry` - Tracing support

## Motivation

Python has many "worker-queue" libraries and frameworks, such as:

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


## Backend support

|Backend|Development Status|Description|
|--|---|---|
|Stub|Beta|In-memory broker implementation, useful for tests|
|Nats|Beta|[Docs](https://docs.nats.io/)|
|Nats Jetstream|Beta|[Docs](https://docs.nats.io/nats-concepts/jetstream)|
|Apache Kafka|Beta|[Docs](https://kafka.apache.org/)|
|RabbitMQ|Planning|[Docs](https://www.rabbitmq.com/)|
|Redis|Planning|[Docs](https://redis.io/docs/manual/pubsub/)|
|Google Cloud PubSub|Planning|[Docs](https://pypi.org/project/gcloud-aio-pubsub/)|
