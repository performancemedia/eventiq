from typing import Any

import ormsgpack
from pydantic_core import to_jsonable_python

from eventiq import Encoder

from ..exceptions import DecodeError, EncodeError


class MsgPackEncoder(Encoder):
    """
    Message Pack encoder implementation using `ormsgpack` library.
    """

    CONTENT_TYPE = "application/x-msgpack"

    def encode(self, data: Any) -> bytes:
        try:
            return ormsgpack.packb(
                data,
                option=ormsgpack.OPT_NON_STR_KEYS | ormsgpack.OPT_SERIALIZE_NUMPY,
                default=to_jsonable_python,
            )
        except ormsgpack.MsgpackEncodeError as e:
            raise EncodeError from e

    def decode(self, data: bytes) -> Any:
        try:
            return ormsgpack.unpackb(data)
        except ormsgpack.MsgpackDecodeError as e:
            raise DecodeError from e
