import json
from typing import Any

from pydantic_core import to_jsonable_python

from eventiq import Encoder

from ..exceptions import DecodeError, EncodeError


class JsonEncoder(Encoder):
    """
    Default encoder, serializes CloudEvent models to json objects.
    """

    CONTENT_TYPE = "application/json"

    def encode(self, data: Any) -> bytes:
        try:
            return json.dumps(data, default=to_jsonable_python).encode("utf-8")
        except TypeError as e:
            raise EncodeError from e

    def decode(self, data: bytes) -> Any:
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise DecodeError from e
