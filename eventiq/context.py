from contextvars import ContextVar
from typing import TypedDict
from uuid import UUID


class Ctx(TypedDict, total=False):
    id: UUID
    trace_id: UUID


context: ContextVar[Ctx] = ContextVar("context", default=Ctx())
