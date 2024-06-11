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
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)

*Note: This package is under active development and is not recommended for production use*

---
Version: 0.2.3

Documentation: https://performancemedia.github.io/eventiq/

Repository: https://github.com/performancemedia/eventiq

---
## About

The package utilizes `anyio` and `pydantic` as the only required dependencies.
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
- And more coming

## Optional Dependencies
  - `cli` - `typer`
  - broker of choice: `nats`, `kafka`, `rabbitmq`, `redis`, `pubsub`
  - custom message serializers: `msgpack`, `orjson`
  - `prometheus` - Metric exposure via `PrometheusMiddleware`
  - `opentelemetry` - tracing support

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
# main.py
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

```
## Running the service

```shell
eventiq run main:service
```

## Scaling

Each message is load-balanced (depending on broker) between all service instances with the same `name`.
To scale number of processes you can use containers (docker/k8s), [supervisor](http://supervisord.org/),
or web server like gunicorn.

## Features

- Modern, `asyncio` based python 3.8+ syntax
- Minimal dependencies, only `anyio` and `pydantic` are required
- Automatic message parsing based on type annotations (like FastAPI)
- Code hot-reload
- Highly scalable: each service can process hundreds of tasks concurrently,
    all messages are load balanced between all instances by default
- Resilient - at least once delivery for all messages by default
- Customizable & pluggable message encoders (json, msgpack, custom)
- Multiple broker support (Nats, Kafka, Rabbitmq, Redis, PubSub, and more coming)
- Easily extensible via Middlewares and Plugins
- Cloud Events standard as base message structure (no more python specific `*args` and `**kwargs` in messages)
- AsyncAPI documentation generation from code
- Twelve factor app approach - stdout logging, configuration through environment variables
- Out-of-the-box integration with Prometheus (metrics) and OpenTelemetry (tracing)
- Application bootstrap via `.yaml` file (see examples/configuration)
