from typing import Any, List, Optional

from pydantic import BaseSettings, Field, validator

from eventiq.utils.imports import import_from_string

from .middleware import Middleware


class Settings(BaseSettings):
    broker_class: str = Field(..., env="BROKER_CLASS")

    def get_broker_class(self):
        return import_from_string(self.broker_class)


class BrokerSettings(BaseSettings):
    description: Optional[str] = None
    middlewares: Optional[List["Middleware"]] = None
    encoder: Optional[Any] = Field(None, env="BROKER_ENCODER_CLASS")

    @validator("encoder", pre=True)
    def resolve_encoder(cls, v):
        if isinstance(v, str):
            v = import_from_string(v)
        return v
