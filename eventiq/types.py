from __future__ import annotations

from enum import Enum
from typing import Any, Optional, Protocol, TypedDict, Union
from uuid import UUID

ID = Union[UUID, str]


Tags = Optional[list[Union[str, Enum]]]


class ServerInfo(TypedDict, total=False):
    host: str | None
    protocol: str
    protocolVersion: str | None
    pathname: str | None


class TagMeta(TypedDict):
    name: str
    description: str


class ResultBackend(Protocol):
    async def get_result(self, service: str, message_id: ID) -> Any | None:
        ...
