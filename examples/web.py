from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse, Response

from eventiq import CloudEvent, Service
from eventiq.asyncapi import PublishInfo
from eventiq.backends.nats import JetStreamBroker
from eventiq.backends.nats.plugins import JetStreamResultBackend
from eventiq.contrib.fastapi import FastAPIServicePlugin
from eventiq.types import ID

broker = JetStreamBroker(url="nats://localhost:4222")
results = JetStreamResultBackend(broker)

service = Service(
    name="example-service",
    broker=broker,
    publish_info=[
        PublishInfo.s(
            CloudEvent,
            topic="events.topic",
            description="Published on /publish endpoint",
        )
    ],
)


app = FastAPI()

FastAPIServicePlugin(service).configure_app(
    app, healthcheck_url="/healthz", async_api_url="/asyncapi"
)


@service.subscribe("events.topic", name="test_consumer", store_results=True)
async def handler(message: CloudEvent):
    print(f"Received Message {message.id} with data: {message.data}")
    return message.data


@app.post("/publish", status_code=202, response_model=CloudEvent)
async def publish_event(data: Any = Body(...)):
    event: CloudEvent[Any] = CloudEvent(topic="events.topic", data=data)
    await service.publish(event)
    return event


@app.get("/{message_id}")
async def get_result(message_id: ID):
    res: Any = await results.get_result(service.name, message_id)
    if res is None:
        return Response(status_code=404, content="Key not found")
    return JSONResponse(content=res)
