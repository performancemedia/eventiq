import numpy as np
import pytest
from pydantic import ConfigDict

from eventiq import CloudEvent
from eventiq.encoders import get_default_encoder
from eventiq.encoders.json import JsonEncoder
from eventiq.encoders.msgpack import MsgPackEncoder
from eventiq.encoders.orjson import OrjsonEncoder
from eventiq.encoders.pickle import PickleEncoder


@pytest.mark.parametrize(
    "encoder", (JsonEncoder(), OrjsonEncoder(), MsgPackEncoder(), PickleEncoder())
)
@pytest.mark.parametrize("data", (1, "2", 3.0, [None], {"key": "value", "1": 2}))
def test_encoders_simple_data(encoder, data):
    encoded = encoder.encode(data)
    assert isinstance(encoded, bytes)
    decoded = encoder.decode(encoded)
    assert decoded == data


@pytest.mark.parametrize("encoder", (JsonEncoder(), OrjsonEncoder(), PickleEncoder()))
@pytest.mark.parametrize("data", (1, "2", 3.0, [None], {"key": "value", "1": 2}))
def test_encoder_cloud_events(encoder, data):
    ce = CloudEvent(topic="test.topic", data=data, type="TestEvent")
    ce_dict = ce.model_dump()
    assert data == ce_dict["data"]
    encoded = encoder.encode(ce_dict)
    assert isinstance(encoded, bytes)
    decoded = encoder.decode(encoded)
    assert decoded["data"] == ce_dict["data"]


@pytest.mark.parametrize(
    "encoder", (OrjsonEncoder(), MsgPackEncoder(), PickleEncoder())
)
def test_encoders_numpy_data(encoder):
    class NumpyCe(CloudEvent[np.ndarray]):
        model_config = ConfigDict(arbitrary_types_allowed=True)

    ce = NumpyCe(topic="test.topic", data=np.ones(1280).astype(np.float32))
    encoded = encoder.encode(ce.model_dump())
    assert isinstance(encoded, bytes)
    decoded = encoder.decode(encoded)
    assert np.array_equal(ce.data, decoded["data"])


def test_get_default_encoder_cached():
    enc1 = get_default_encoder()
    enc2 = get_default_encoder()
    assert enc1 is enc2
