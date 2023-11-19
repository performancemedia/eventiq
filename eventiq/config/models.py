from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict

from eventiq import Broker
from eventiq.consumer import FnConsumer, GenericConsumer
from eventiq.imports import ImportedType
from eventiq.types import Encoder, MessageHandlerT, TagMeta


def resolve_nested(v: Any):
    if isinstance(v, TypedModel):
        return v.build()
    elif isinstance(v, list):
        v = [resolve_nested(i) for i in v]
    if isinstance(v, dict):
        if "type" in v:
            return TypedModel.model_validate(v).build()
        else:
            for key, value in v.items():
                v[key] = resolve_nested(value)
    return v


T = TypeVar("T")


class TypedModel(BaseModel, Generic[T]):
    type: ImportedType[T]

    def build(self):
        kwargs = self.model_dump(exclude={"type"}, exclude_none=True)
        for k, v in kwargs.items():
            kwargs[k] = resolve_nested(v)
        return self.type(**kwargs)

    model_config = ConfigDict(extra="allow")


class BrokerConfig(TypedModel[Broker]):
    encoder: TypedModel[Encoder]
    middlewares: List[TypedModel]
    context: Dict[str, Union[TypedModel, Any]] = {}


class ConsumerConfig(TypedModel[MessageHandlerT]):
    topic: str
    name: Optional[str] = None
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
    title: Optional[str] = None
    version: str = "0.1.0"
    description: str = ""
    tags_metadata: List[TagMeta] = []
    instance_id_generator: Optional[ImportedType[Callable[[], str]]] = None
    consumers: List[ConsumerConfig]


class AppConfig(BaseModel):
    brokers: Dict[str, BrokerConfig]
    services: List[ServiceConfig]
