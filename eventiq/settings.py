from typing import List, Optional, Union

from pydantic import BaseSettings, Field

from eventiq.utils.imports import ImportedType

from .middleware import Middleware
from .types import Encoder


class BrokerSettings(BaseSettings):
    description: Optional[str] = None
    middlewares: Optional[List[Middleware]] = None
    encoder: Optional[Union[Encoder, ImportedType]] = Field(
        None, env="BROKER_ENCODER_CLASS"
    )


class ServiceSettings(BaseSettings):
    name: str
    title: Optional[str] = None
    version: str = "0.1.0"
    description: str = ""
