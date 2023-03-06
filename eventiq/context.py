from contextvars import ContextVar
from typing import Any

context: ContextVar[dict[str, Any]] = ContextVar("context", default={})
