from typing import List, Optional

from pydantic import BaseSettings, Field

from eventiq.utils.imports import ImportedType

from .middleware import Middleware


class BrokerSettings(BaseSettings):
    broker_class: ImportedType = Field(..., env="BROKER_CLASS")
    description: Optional[str] = None
    middlewares: Optional[List[Middleware]] = None
    encoder: Optional[ImportedType] = Field(None, env="BROKER_ENCODER_CLASS")


class ServiceSettings(BaseSettings):
    broker_settings: BrokerSettings = Field(default_factory=BrokerSettings)
    name: str
    title: Optional[str] = None
    version: str = "0.1.0"
    description: str = ""
