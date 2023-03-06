import json
from typing import Any

from pydantic.json import pydantic_encoder

from ..exceptions import DecodeError, EncodeError


class JsonEncoder:
    """
    Default encoder, serializes CloudEvent models to json objects.
    """

    CONTENT_TYPE = "application/json"

    @staticmethod
    def encode(data: Any) -> bytes:
        try:
            return json.dumps(data, default=pydantic_encoder).encode("utf-8")
        except TypeError as e:
            raise EncodeError from e

    @staticmethod
    def decode(data: bytes) -> Any:
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise DecodeError from e
