from datetime import datetime, timedelta
from typing import Any, Dict, Generic, Optional

from pydantic import Extra, Field, validator
from pydantic.fields import PrivateAttr
from pydantic.generics import GenericModel

from .message import Message
from .types import ID, D
from .utils import str_uuid
from .utils.datetime import utc_now


class CloudEvent(GenericModel, Generic[D]):
    specversion: Optional[str] = "1.0"
    content_type: str = Field("application/json", alias="datacontenttype")
    id: ID = Field(default_factory=str_uuid)
    time: datetime = Field(default_factory=utc_now)
    topic: str = Field(..., alias="subject")
    type: Optional[str] = None
    source: Optional[str] = None
    data: Optional[D] = None
    trace_ctx: Dict[str, str] = {}

    _raw: Optional[Any] = PrivateAttr()

    def __eq__(self, other):
        if not isinstance(other, CloudEvent):
            return False
        return self.id == other.id

    @validator("type", allow_reuse=True, always=True, pre=True)
    def get_type_from_cls_name(cls, v) -> str:
        return v or cls.__name__

    @property
    def raw(self) -> Message:
        if self._raw is None:
            raise AttributeError("raw property accessible only for incoming messages")
        return self._raw

    def _set(self, name: str, value: Any):
        object.__setattr__(self, name, value)

    def set_source(self, value: str) -> None:
        self._set("source", value)

    def set_raw(self, value: Message):
        self._set("_raw", value)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        return super().dict(**kwargs)

    @classmethod
    def new(cls, obj: D, **kwargs):
        return cls(data=obj, **kwargs)

    @property
    def age(self) -> timedelta:
        return utc_now() - self.time

    def fail(self):
        self.raw.fail()

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True
        extra = Extra.allow
        # events are immutable, however it's sometimes useful to set source or traceid for unpublished events
        allow_mutation = False
