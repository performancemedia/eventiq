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
    trace_id: ID = Field(default_factory=str_uuid, alias="traceid")
    time: datetime = Field(default_factory=utc_now)
    topic: str = Field(..., alias="subject")
    type: Optional[str] = None
    source: Optional[str] = None
    data: Optional[D] = None

    _raw: Optional[Any] = PrivateAttr()

    def __eq__(self, other):
        if not isinstance(other, CloudEvent):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash((self.trace_id, self.id))

    @validator("type", allow_reuse=True, always=True, pre=True)
    def get_type_from_cls_name(cls, v) -> str:
        return v or cls.__name__

    @property
    def raw(self) -> Message:
        if self._raw is None:
            raise AttributeError("raw property accessible only for incoming messages")
        return self._raw

    def set_source(self, value: str) -> None:
        self._set("source", value)

    def set_trace_id(self, value: str) -> None:
        self._set("trace_id", value)

    def _set(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        return super().dict(**kwargs)

    @classmethod
    def new(cls, obj: D, **kwargs):
        return cls(data=obj, **kwargs)

    @property
    def context(self) -> Dict[str, Any]:
        return {"trace_id": self.trace_id, "id": self.id}

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


class WorkflowEvent(CloudEvent):
    workflow: ID
    run_id: ID
    follows_from: Optional[ID]
