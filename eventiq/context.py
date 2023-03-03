from contextvars import ContextVar
from uuid import UUID

from typing_extensions import TypedDict


class Ctx(TypedDict, total=False):
    id: UUID
    trace_id: UUID


context: ContextVar[Ctx] = ContextVar("context", default=Ctx())
