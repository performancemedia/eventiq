from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from .imports import ImportedType
from .middleware import Middleware
from .types import Encoder


class BrokerSettings(BaseSettings):
    default_consumer_timeout: int = Field(
        300, validation_alias="DEFAULT_CONSUMER_TIMEOUT"
    )
    description: Optional[str] = None
    middlewares: Optional[list[Middleware]] = None
    encoder: Optional[ImportedType[Encoder]] = Field(
        None, validation_alias="BROKER_ENCODER_CLASS"
    )


class ServiceSettings(BaseSettings):
    name: str
    title: Optional[str] = None
    version: str = "0.1.0"
    description: str = ""
