from eventiq.backends.nats import NatsBroker


def test_nats_broker_topic_pattern():
    broker = NatsBroker()
    pattern = "events.{param}.*"
    result = broker.format_topic(pattern)
    assert result == "events.*.>"
