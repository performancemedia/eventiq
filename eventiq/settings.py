from typing import Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from .encoder import Encoder
from .imports import ImportedType
from .middleware import Middleware


class BrokerSettings(BaseSettings):
    default_consumer_timeout: int = 300
    description: Optional[str] = None
    middlewares: Optional[list[Middleware]] = None
    encoder: Optional[ImportedType[Encoder]] = None
    validate_error_delay: Optional[int] = 3600 * 12

    model_config = SettingsConfigDict(env_prefix="BROKER_")


class UrlBrokerSettings(BrokerSettings):
    url: str
    connection_options: dict[str, Any] = {}


class ServiceSettings(BaseSettings):
    name: str
    title: Optional[str] = None
    version: str = "0.1.0"
    description: str = ""
