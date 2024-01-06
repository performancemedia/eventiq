import pickle  # nosec
from typing import Any

import cloudpickle


class CloudPickleEncoder:
    """
    CloudPickle encoder implementation
    """

    CONTENT_TYPE = "application/octet-stream"

    @staticmethod
    def encode(data: Any) -> bytes:
        return cloudpickle.dumps(data)

    @staticmethod
    def decode(data: bytes) -> Any:
        return pickle.loads(data)  # nosec
