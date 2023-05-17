from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Extra

from eventiq.consumer import FnConsumer, GenericConsumer
from eventiq.types import TagMeta
from eventiq.utils.imports import ImportedType


def resolve_nested(v: Any):
    if isinstance(v, TypedModel):
        return v.build()
    elif isinstance(v, list):
        v = [resolve_nested(i) for i in v]
    if isinstance(v, dict):
        if "type" in v:
            return TypedModel.parse_obj(v).build()
        else:
            for key, value in v.items():
                v[key] = resolve_nested(value)
    return v


class TypedModel(BaseModel):
    type: ImportedType

    def build(self):
        kwargs = self.dict(exclude={"type"}, exclude_none=True)
        for k, v in kwargs.items():
            kwargs[k] = resolve_nested(v)
        return self.type(**kwargs)

    class Config:
        extra = Extra.allow


class BrokerConfig(TypedModel):
    encoder: TypedModel
    middlewares: List[TypedModel]
    context: Dict[str, Union[TypedModel, Any]] = {}


class ConsumerConfig(TypedModel):
    topic: str
    name: Optional[str]
    timeout: int = 120
    dynamic: bool = False

    def build(self):
        if callable(self.type) and not (
            isinstance(self.type, type) and issubclass(self.type, GenericConsumer)
        ):
            self.__dict__["fn"] = self.type
            self.type = FnConsumer
        return super().build()


class ServiceConfig(BaseModel):
    name: str
    broker: str = "default"
    title: Optional[str]
    version: str = "0.1.0"
    description: str = ""
    tags_metadata: List[TagMeta] = []
    instance_id_generator: Optional[ImportedType]
    consumers: List[ConsumerConfig]


class AppConfig(BaseModel):
    brokers: Dict[str, BrokerConfig]
    services: List[ServiceConfig]
