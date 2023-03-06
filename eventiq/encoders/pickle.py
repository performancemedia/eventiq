import pickle  # nosec
from typing import Any


class PickleEncoder:
    """
    Pickle encoder implementation. Allows to pass/serialize python native objects,
    but it is not recommended. See warning: <https://docs.python.org/3/library/pickle.html>
    """

    CONTENT_TYPE = "application/octet-stream"

    @staticmethod
    def encode(data: Any) -> bytes:
        return pickle.dumps(data)

    @staticmethod
    def decode(data: bytes) -> Any:
        return pickle.loads(data)  # nosec
