from contextvars import ContextVar
from typing import Any, Dict

from eventiq.utils import str_uuid

context: ContextVar[Dict[str, Any]] = ContextVar(
    "context", default={"trace_id": str_uuid()}
)


def set_global_context(ctx: ContextVar[Dict[str, Any]]) -> None:
    global context
    context = ctx
