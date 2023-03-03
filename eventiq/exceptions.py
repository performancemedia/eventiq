from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eventiq.models import CloudEvent


class ConfigurationError(Exception):
    pass


class BrokerError(Exception):
    pass


class PublishError(BrokerError):
    pass


class MessageError(BrokerError):
    def __init__(self, message: CloudEvent):
        self.message = message


class DecodeError(Exception):
    def __init__(self, data: bytes, error):
        self.data = data
        self.error = error


class Skip(Exception):
    """Raise exception to skip message without processing and/or retrying"""


class Fail(Exception):
    """Fail message without retrying"""


class Reject(Exception):
    """Reject (nack) message"""

    def __init__(self, reason: str):
        self.reason = reason


class Retry(Exception):
    """
    Utility exception for retrying message.
    Handling must be implemented in middleware
    """

    def __init__(self, delay: int | None = None):
        self.delay = delay
