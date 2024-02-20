from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from eventiq import Broker
from eventiq.consumer import FnConsumer, GenericConsumer, MessageHandlerT
from eventiq.encoder import Encoder
from eventiq.imports import ImportedType
from eventiq.types import TagMeta


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
    middlewares: list[TypedModel]


class ConsumerConfig(TypedModel[MessageHandlerT]):
    topic: str | None = None
    name: str | None = None
    timeout: int = 120
    dynamic: bool = False
    encoder: TypedModel[Encoder] | None = None

    def build(self):
        if callable(self.type) and not (
            isinstance(self.type, type) and issubclass(self.type, GenericConsumer)
        ):
            self.__dict__["fn"] = self.type
            self.type = FnConsumer
        return super().build()


class ServiceConfig(BaseModel):
    name: str
    brokers: list[str]
    title: str | None = None
    version: str = "0.1.0"
    description: str = ""
    tags_metadata: list[TagMeta] = []
    instance_id_generator: ImportedType[Callable[[], str]] | None = None
    consumers: list[ConsumerConfig]


class AppConfig(BaseModel):
    brokers: dict[str, BrokerConfig]
    services: list[ServiceConfig]
