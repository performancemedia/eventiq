import pickle  # nosec
from typing import Any


class PickleEncoder:
    CONTENT_TYPE = "application/octet-stream"

    @staticmethod
    def encode(data: Any) -> bytes:
        return pickle.dumps(data)

    @staticmethod
    def decode(data: bytes) -> Any:
        return pickle.loads(data)  # nosec
