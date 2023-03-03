## Integration with web frameworks

Unlike [Nameko](https://www.nameko.io/) or [Faust](https://faust.readthedocs.io/en/latest/) which try 
to provide basic utilities for adding http/rest utilities to their framework using
[werkzeug](https://werkzeug.palletsprojects.com/en/2.2.x/) or [aiohttp](https://docs.aiohttp.org/en/stable/),
eventiq allows you to integrate `service` to an existing web app like
[FastAPI](https://fastapi.tiangolo.com/).

## Example:

```python
from typing import Any

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse, Response
from eventiq import Service, CloudEvent
from eventiq.middlewares import HealthCheckMiddleware
from eventiq.backends.nats import JetStreamBroker, NatsJetStreamResultMiddleware
from eventiq.web import include_service


broker = JetStreamBroker(url="nats://localhost:4222")
kv = NatsJetStreamResultMiddleware(bucket="test")

broker.add_middleware(HealthCheckMiddleware())
broker.add_middleware(kv)

service = Service(name="example-service", broker=broker)


app = FastAPI()

include_service(app=app, service=service, add_health_endpoint=True)


@service.subscribe("events.topic", name="test_consumer", store_results=True)
async def handler(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")
    return message.data


@app.post("/publish", status_code=202, response_model=CloudEvent)
async def publish_event(data: Any = Body(...)):
    event = CloudEvent(topic="events.topic", data=data)
    await service.publish_event(event)
    return event

@app.get("/{consumer}/{key}")
async def get_result(consumer: str, key: str):
    res = await kv.get(f"{consumer}:{key}")
    if res is None:
        return Response(status_code=404, content="Key not found")
    return JSONResponse(content=res)

```