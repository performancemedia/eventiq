## Integration with web frameworks

Unlike [Nameko](https://www.nameko.io/) or [Faust](https://faust.readthedocs.io/en/latest/) which try 
to provide basic utilities for adding http/rest utilities to their framework using
[werkzeug](https://werkzeug.palletsprojects.com/en/2.2.x/) or [aiohttp](https://docs.aiohttp.org/en/stable/),
eventiq allows you to integrate `service` to an existing web app like
[FastAPI](https://fastapi.tiangolo.com/).

## FastAPI Example

```python
from typing import Any
from uuid import UUID
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse, Response
from eventiq import Service, CloudEvent
from eventiq.middlewares import HealthCheckMiddleware
from eventiq.backends.nats import JetStreamBroker, JetStreamResultBackend
from eventiq.contrib.fastapi import FastAPIServicePlugin

broker = JetStreamBroker(url="nats://localhost:4222")
kv = JetStreamResultBackend(broker)

broker.add_middleware(HealthCheckMiddleware())

service = Service(name="example-service", broker=broker)


app = FastAPI()

FastAPIServicePlugin(service, app, healthcheck_url="/healthz")


@service.subscribe("events.topic", name="test_consumer", store_results=True)
async def handler(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")
    return message.data


@app.post("/publish", status_code=202, response_model=CloudEvent)
async def publish_event(data: Any = Body(...)):
    event = CloudEvent(topic="events.topic", data=data)
    await service.publish_event(event)
    return event

@app.get("/{message_id}")
async def get_result(message_id: UUID):
    res = await kv.get_result(service.name, message_id)
    if res is None:
        return Response(status_code=404, content="Key not found")
    return JSONResponse(content=res)

```