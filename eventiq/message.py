from __future__ import annotations

from typing import Generic

from .types import RawMessage


class Message(Generic[RawMessage]):
    def __init__(self, message: RawMessage):
        self._message = message
        self._failed = False
        self._retry_delay: int | None = None

    def __getattr__(self, item):
        return getattr(self._message, item)

    def __str__(self):
        return str(self._message)

    @property
    def delay(self):
        return self._retry_delay

    @delay.setter
    def delay(self, value: int):
        if value < 0:
            raise ValueError("Cannot set negative delay")
        self._retry_delay = value

    @property
    def failed(self) -> bool:
        return self._failed

    def fail(self) -> None:
        self._failed = True
