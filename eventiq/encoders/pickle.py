import pickle  # nosec
from typing import Any

from eventiq import Encoder
from eventiq.exceptions import DecodeError, EncodeError


class PickleEncoder(Encoder):
    """
    Pickle encoder implementation. Allows to pass/serialize python native objects,
    but it is not recommended. See warning: <https://docs.python.org/3/library/pickle.html>
    """

    CONTENT_TYPE = "application/octet-stream"

    def encode(self, data: Any) -> bytes:
        try:
            return pickle.dumps(data)
        except Exception as e:
            raise EncodeError from e

    def decode(self, data: bytes) -> Any:
        try:
            return pickle.loads(data)  # nosec
        except (pickle.UnpicklingError, TypeError) as e:
            raise DecodeError from e
