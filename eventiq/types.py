from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Optional,
    Protocol,
    Type,
    TypedDict,
    TypeVar,
    Union,
)
from uuid import UUID

if TYPE_CHECKING:
    from eventiq import CloudEvent, GenericConsumer

ID = Union[str, int, UUID]


RawMessage = TypeVar("RawMessage")

T = TypeVar("T", bound="CloudEvent")
D = TypeVar("D")


class TagMeta(TypedDict):
    name: str
    description: str


class Encoder(Protocol):
    """
    Encoder object protocol.
    """

    CONTENT_TYPE: str

    def encode(self, data: Any) -> bytes:
        """
        Serialize object to bytes
        :param data: input value, usually CloudEvent.dict()
        :return: raw content as bytes
        """

    def decode(self, data: bytes) -> Any:
        """
        Deserialize bytes to python object
        :param data: input bytes
        :return: de-serialized object
        """


FT = Callable[["CloudEvent"], Awaitable[Optional[Any]]]
MessageHandlerT = Union[Type["GenericConsumer"], FT]

ExcHandler = Callable[["CloudEvent", Exception], Awaitable]
