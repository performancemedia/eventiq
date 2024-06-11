import asyncio

from eventiq import CloudEvent, Service
from eventiq.backends.stub import StubBroker


def test_service(service):
    assert isinstance(service, Service)
    assert isinstance(service.default_broker, StubBroker)
    assert service.name == "test_service"


async def test_service_scope(running_service: Service, ce):
    assert isinstance(running_service, Service)
    assert running_service.default_broker is not None
    assert isinstance(running_service.default_broker, StubBroker)

    queue: asyncio.Queue = running_service.default_broker.topics[ce.topic]
    running_service.default_broker.wait_on_publish = False
    await running_service.publish(ce)
    msg = await queue.get()
    queue.task_done()
    decoded = running_service.default_broker.encoder.decode(msg.data)
    ce2 = CloudEvent.model_validate(decoded)
    assert ce.model_dump() == ce2.model_dump()


async def test_consumer_called(running_service: Service, ce: CloudEvent, mock_consumer):
    # publishing event, returns a dict with topics and events (Futures)
    await running_service.publish(ce)
    # so here we're sure that the consumer was called
    mock_consumer.assert_awaited_once_with(ce)
    # we're even sure that the consumer was called with the right event (!)
