from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse, Response

from eventiq import CloudEvent, Service
from eventiq.backends.redis import RedisBroker, RedisResultBackend
from eventiq.contrib.fastapi import FastAPIServicePlugin
from eventiq.types import ID

broker: RedisBroker = RedisBroker(url="redis://localhost:6379/0")
results = RedisResultBackend(broker)

service = Service(name="example-service", broker=broker)


app = FastAPI()

FastAPIServicePlugin(service).configure_app(app, healthcheck_url="/healthz")


@service.subscribe("events.*", name="test_consumer", store_results=True)
async def handler(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")
    return message.data


@app.post("/publish", status_code=202, response_model=CloudEvent)
async def publish_event(data: Any = Body(...)):
    event: CloudEvent[Any] = CloudEvent(topic="events.nested.topic", data=data)
    await service.publish(event)
    return event


@app.get("/{message_id}")
async def get_result(message_id: ID):
    res: Any = await results.get_result(service.name, message_id)
    if res is None:
        return Response(status_code=404, content="Key not found")
    return JSONResponse(content=res)
