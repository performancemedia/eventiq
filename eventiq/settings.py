from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .encoder import Encoder
from .imports import ImportedType
from .middleware import Middleware


class BrokerSettings(BaseSettings):
    default_consumer_timeout: int = Field(
        300, validation_alias="DEFAULT_CONSUMER_TIMEOUT"
    )
    description: Optional[str] = None
    middlewares: Optional[list[Middleware]] = None
    encoder: Optional[ImportedType[Encoder]] = Field(
        None, validation_alias="ENCODER_CLASS"
    )

    model_config = SettingsConfigDict(env_prefix="BROKER_")


class UrlBrokerSettings(BrokerSettings):
    url: str
    connection_options: dict[str, Any] = {}


class ServiceSettings(BaseSettings):
    name: str
    title: Optional[str] = None
    version: str = "0.1.0"
    description: str = ""
