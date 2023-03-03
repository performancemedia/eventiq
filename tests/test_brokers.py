import pytest

from eventiq.backends.kafka import KafkaBroker
from eventiq.backends.nats import JetStreamBroker, NatsBroker
from eventiq.backends.rabbitmq import RabbitmqBroker
from eventiq.broker import Broker

backends = [NatsBroker, JetStreamBroker, KafkaBroker, RabbitmqBroker]


@pytest.mark.parametrize("broker", backends)
def test_is_subclass(broker):
    assert issubclass(broker, Broker)
