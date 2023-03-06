from typing import Any

import ormsgpack
from pydantic.json import pydantic_encoder

from ..exceptions import DecodeError, EncodeError


class MsgPackEncoder:
    """
    Message Pack encoder implementation using `ormsgpack` library.
    """

    CONTENT_TYPE = "application/x-msgpack"

    @staticmethod
    def encode(data: Any) -> bytes:
        try:
            return ormsgpack.packb(data, default=pydantic_encoder)
        except ormsgpack.MsgpackEncodeError as e:
            raise EncodeError from e

    @staticmethod
    def decode(data: bytes) -> Any:
        try:
            return ormsgpack.unpackb(data)
        except ormsgpack.MsgpackDecodeError as e:
            raise DecodeError from e
