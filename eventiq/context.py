from contextvars import ContextVar
from typing import Any, Dict

context: ContextVar[Dict[str, Any]] = ContextVar("context", default={})


def set_global_context(ctx: ContextVar[Dict[str, Any]]) -> None:
    global context
    context = ctx
