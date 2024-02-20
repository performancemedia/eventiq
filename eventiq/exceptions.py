from __future__ import annotations


class EventiqError(Exception):
    """Base exception for Eventiq"""


class ConfigurationError(EventiqError):
    """Raised by framework when invalid configuration is supplied"""


class BrokerError(EventiqError):
    """Base Exception for broker related errors"""


class ConsumerError(EventiqError):
    """Base Exception for consumer related errors"""


class ConsumerTimeoutError(ConsumerError):
    """Raised when consumer times out"""

    def __str__(self) -> str:
        return "ConsumerTimeoutError"


class PublishError(BrokerError):
    """Raised when publishing a message fails"""


class EncoderError(EventiqError):
    """Base Encoder error"""


class EncodeError(EncoderError):
    """Error encoding message"""


class DecodeError(EncoderError):
    """Error decoding message"""


class MessageError(EventiqError):
    """Base message processing error"""

    def __init__(self, reason: str):
        self.reason = reason

    def __str__(self):
        return f"{self.__class__.__name__}: {self.reason}"


class Skip(MessageError):
    """Raise exception to skip message without processing and/or retrying"""


class Fail(MessageError):
    """Fail message without retrying"""


class Retry(MessageError):
    """
    Utility exception for retrying message.
    RetryMiddleware must be added
    """

    def __init__(self, reason: str | None = None, delay: int | None = None):
        self.reason = reason or "unknown"
        self.delay = delay
