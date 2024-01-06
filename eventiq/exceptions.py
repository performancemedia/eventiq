from __future__ import annotations


class ConfigurationError(Exception):
    """Raised by framework when invalid configuration is supplied"""


class BrokerError(Exception):
    """Base Exception for broker related errors"""


class PublishError(BrokerError):
    """Raised when publishing a message fails"""


class EncoderError(Exception):
    """Base Encoder error"""


class EncodeError(EncoderError):
    """Error encoding message"""


class DecodeError(EncoderError):
    """Error decoding message"""


class MessageError(Exception):
    """Base message processing error"""


class Skip(MessageError):
    """Raise exception to skip message without processing and/or retrying"""


class Fail(MessageError):
    """Fail message without retrying"""


class Retry(MessageError):
    """
    Utility exception for retrying message.
    RetryMiddleware must be added
    """

    def __init__(self, reason: str | None = None, *, delay: int | None = None):
        self.reason = reason or "unknown"
        self.delay = delay

    def __str__(self) -> str:
        # TODO: make prettier
        return f"Retry: {self.reason=} {self.delay=}"

    def __repr__(self) -> str:
        return str(self)
