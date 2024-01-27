from typing import Any

import orjson
from pydantic_core import to_jsonable_python

from eventiq import Encoder

from ..exceptions import DecodeError, EncodeError


class OrjsonEncoder(Encoder):
    """
    Json encoder which utilizes orjson library.
    """

    CONTENT_TYPE = "application/json"

    def encode(self, data: Any) -> bytes:
        try:
            return orjson.dumps(
                data,
                option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
                default=to_jsonable_python,
            )
        except TypeError as e:
            raise EncodeError from e

    def decode(self, data: bytes) -> Any:
        try:
            return orjson.loads(data)
        except orjson.JSONDecodeError as e:
            raise DecodeError from e
