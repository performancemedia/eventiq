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


class Skip(Exception):
    """Raise exception to skip message without processing and/or retrying"""


class Fail(Exception):
    """Fail message without retrying"""


class Retry(Exception):
    """
    Utility exception for retrying message.
    RetryMiddleware must be added
    """

    def __init__(self, delay: int | None = None):
        self.delay = delay
