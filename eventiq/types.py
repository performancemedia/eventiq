from __future__ import annotations

from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    List,
    Optional,
    Protocol,
    Type,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)
from uuid import UUID

if TYPE_CHECKING:
    from . import CloudEvent, GenericConsumer


ID = Union[UUID, str]


RawMessage = TypeVar("RawMessage")

T = TypeVar("T", bound="CloudEvent")
D = TypeVar("D")

Tags = Optional[List[Union[str, Enum]]]


class TagMeta(TypedDict):
    name: str
    description: str


@runtime_checkable
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


FT = Callable[["CloudEvent"], Union[Awaitable[Optional[Any]], Optional[Any]]]
MessageHandlerT = Union[Type["GenericConsumer"], FT]

ExcHandler = Callable[["CloudEvent", Exception], Awaitable]


class ResultBackend(Protocol):
    async def get_result(self, service: str, message_id: ID) -> Any | None:
        ...
