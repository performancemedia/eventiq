from abc import ABC, abstractmethod
from typing import Any


class Encoder(ABC):
    """
    Encoder object protocol.
    """

    CONTENT_TYPE: str

    @abstractmethod
    def encode(self, data: Any) -> bytes:
        """
        Serialize object to bytes
        :param data: input value, usually CloudEvent.model_dump()
        :return: raw content as bytes
        """

    @abstractmethod
    def decode(self, data: bytes) -> Any:
        """
        Deserialize bytes to python object
        :param data: input bytes
        :return: de-serialized object
        """
