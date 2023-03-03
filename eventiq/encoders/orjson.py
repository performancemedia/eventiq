from typing import Any

import orjson
from pydantic.json import pydantic_encoder


class OrjsonEncoder:
    CONTENT_TYPE = "application/json"

    @staticmethod
    def encode(data: Any) -> bytes:
        return orjson.dumps(data, default=pydantic_encoder)

    @staticmethod
    def decode(data: bytes) -> Any:
        return orjson.loads(data)
