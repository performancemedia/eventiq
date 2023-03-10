import asyncio

from eventiq import CloudEvent, Service
from eventiq.backends.stub import StubBroker


def test_service(service):
    assert isinstance(service, Service)
    assert isinstance(service.broker, StubBroker)
    assert service.name == "test_service"


async def test_service_scope(running_service: Service, ce):
    assert isinstance(running_service, Service)
    assert running_service.broker is not None
    await running_service.publish_event(ce)
    assert isinstance(running_service.broker, StubBroker)
    queue: asyncio.Queue = running_service.broker.topics[ce.topic]
    msg = await queue.get()
    queue.task_done()
    decoded = running_service.broker.encoder.decode(msg.data)
    ce2 = CloudEvent.parse_obj(decoded)
    assert ce.dict() == ce2.dict()
