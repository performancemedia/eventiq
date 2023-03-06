from contextvars import ContextVar
from typing import Any, Dict

context: ContextVar[Dict[str, Any]] = ContextVar("context", default={})
