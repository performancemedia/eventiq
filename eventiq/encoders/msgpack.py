from typing import Any

import ormsgpack
from pydantic.json import pydantic_encoder


class MsgPackEncoder:
    CONTENT_TYPE = "application/x-msgpack"

    @staticmethod
    def encode(data: Any) -> bytes:
        return ormsgpack.packb(data, default=pydantic_encoder)

    @staticmethod
    def decode(data: bytes) -> Any:
        return ormsgpack.unpackb(data)
