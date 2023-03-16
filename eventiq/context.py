from contextvars import ContextVar
from typing import Any, Dict

from eventiq.utils import str_uuid

context: ContextVar[Dict[str, Any]] = ContextVar(
    "context", default={"trace_id": str_uuid()}
)
