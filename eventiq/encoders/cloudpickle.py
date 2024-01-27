import pickle  # nosec
from typing import Any

import cloudpickle

from eventiq import Encoder
from eventiq.exceptions import DecodeError, EncodeError


class CloudPickleEncoder(Encoder):
    """
    CloudPickle encoder implementation
    """

    CONTENT_TYPE = "application/octet-stream"

    def encode(self, data: Any) -> bytes:
        try:
            return cloudpickle.dumps(data)
        except Exception as e:
            raise EncodeError from e

    def decode(self, data: bytes) -> Any:
        try:
            return pickle.loads(data)  # nosec
        except (pickle.UnpicklingError, TypeError) as e:
            raise DecodeError from e
