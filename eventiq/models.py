from datetime import datetime
from typing import Any, Dict, Generic, Literal, Optional

from pydantic import Extra, Field
from pydantic.fields import ModelField, PrivateAttr
from pydantic.generics import GenericModel

from .types import D, RawMessage
from .utils import str_uuid
from .utils.datetime import utc_now


class CloudEvent(GenericModel, Generic[D]):
    specversion: Optional[str] = "1.0"
    content_type: str = Field("application/json", alias="datacontenttype")
    id: str = Field(default_factory=str_uuid)
    trace_id: str = Field(default_factory=str_uuid, alias="traceid")
    time: datetime = Field(default_factory=utc_now)
    topic: str = Field(..., alias="subject")
    type: Optional[str] = "CloudEvent"
    source: Optional[str] = None
    data: Optional[D] = None

    _raw: Optional[Any] = PrivateAttr()

    def __eq__(self, other):
        if not isinstance(other, CloudEvent):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash((self.trace_id, self.id))

    def __init_subclass__(cls, **kwargs):
        if "abstract" not in kwargs:
            name = kwargs.pop("type", None) or cls.__name__
            cls.__fields__["type"] = ModelField(
                name="type",
                type_=Literal[name],  # type: ignore
                default=name,
                required=False,
                class_validators=None,
                model_config=cls.__config__,
            )

    @property
    def raw(self) -> RawMessage:
        if self._raw is None:
            raise AttributeError("raw property accessible only for incoming messages")
        return self._raw

    def set_source(self, name: str) -> None:
        object.__setattr__(self, "source", name)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        return super().dict(**kwargs)

    @property
    def context(self) -> Dict[str, Any]:
        return self.dict(include={"trace_id", "id"})

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True
        extra = Extra.allow
        allow_mutation = False  # events should be immutable
