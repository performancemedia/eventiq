from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CloudEvent
    from .service import Service


_current_message: ContextVar[CloudEvent | None] = ContextVar(
    "_current_message", default=None
)
_current_service: ContextVar[Service] = ContextVar("_current_service")


def get_current_message():
    global _current_message
    return _current_message.get()


def get_current_service() -> Service:
    global _current_service
    return _current_service.get()
