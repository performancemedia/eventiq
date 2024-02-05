import pytest
from pydantic import ValidationError

from eventiq import CloudEvent


@pytest.fixture
def test_event_cls():
    class TestEvent(CloudEvent[str], topic="events.{type}"):
        pass

    return TestEvent


@pytest.fixture
def test_command_cls():
    class TestCommand(CloudEvent[str], topic="commands.command_a"):
        pass

    return TestCommand


def test_get_default_topic(test_event_cls):
    assert test_event_cls.get_default_topic() == "events.{type}"


@pytest.mark.parametrize(
    "topic", ["some_random_string", "events.type.subtype", "events."]
)
def test_event_incorrect_topic(test_event_cls, topic):
    with pytest.raises(ValidationError):
        test_event_cls(topic=topic, data="test_data")


@pytest.mark.parametrize("topic", ["events.type", "events.type2"])
def test_correct_topic(test_event_cls, topic):
    test_event_cls(topic=topic, data="test_data")


@pytest.mark.parametrize(
    "topic", ["some_random_string", "events.type.subtype", "events."]
)
def test_command_incorrect_topic(test_command_cls, topic):
    with pytest.raises(ValidationError):
        test_command_cls(topic=topic, data="test_data")


def test_command_correct_topic(test_command_cls):
    test_command_cls(data="test_data")
    test_command_cls(data="test_data", topic="commands.command_a")
