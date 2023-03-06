from typing import Any

import orjson
from pydantic.json import pydantic_encoder

from ..exceptions import DecodeError, EncodeError


class OrjsonEncoder:
    """
    Json encoder which utilizes orjson library.
    """

    CONTENT_TYPE = "application/json"

    @staticmethod
    def encode(data: Any) -> bytes:
        try:
            return orjson.dumps(data, default=pydantic_encoder)
        except TypeError as e:
            raise EncodeError from e

    @staticmethod
    def decode(data: bytes) -> Any:
        try:
            return orjson.loads(data)
        except orjson.JSONDecodeError as e:
            raise DecodeError from e
