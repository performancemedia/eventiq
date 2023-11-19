from datetime import datetime, timedelta
from typing import Any, Dict, Generic, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from pydantic.fields import FieldInfo

from .context import get_current_service
from .message import Message
from .types import D
from .utils import utc_now


class CloudEvent(BaseModel, Generic[D]):
    specversion: str = "1.0"
    content_type: str = Field(
        "application/json", alias="datacontenttype", description="Message content type"
    )
    id: UUID = Field(default_factory=uuid4, description="Event ID", repr=True)
    time: datetime = Field(default_factory=utc_now, description="Event created time")
    topic: str = Field(..., alias="subject", description="Message subject (topic)")
    type: str = Field("CloudEvent", description="Event type")
    source: Optional[str] = Field(None, description="Event source (app)")
    data: D = Field(..., description="Event payload")
    dataschema: Optional[AnyUrl] = Field(None, description="Data schema URI")
    tracecontext: Dict[str, str] = Field({}, description="Distributed tracing context")

    _topic_parts: List[str] = PrivateAttr(None)
    _raw: Optional[Any] = PrivateAttr(None)

    def __init_subclass__(cls, **kwargs):
        type_name = kwargs.get("type", cls.__name__)
        cls.model_fields["type"].default = type_name
        cls.model_fields["type"].annotation = Literal[type_name]

        if topic := kwargs.get("topic"):
            cls.model_fields["topic"] = FieldInfo(
                default=topic,
                annotation=Literal[topic],
                alias="subject",
                description="Command subject",
                **kwargs.get("extra", {}),
            )

    def __eq__(self, other):
        if not isinstance(other, CloudEvent):
            return False
        return self.id == other.id

    def __repr__(self):
        return f"{self.type}(id={self.id})"

    @property
    def topic_split(self) -> List[str]:
        if self._topic_parts is None:
            self._topic_parts = self.topic.split(".")
        return self._topic_parts

    @field_validator("type", mode="before")
    @classmethod
    def get_default_type(cls, value, info):
        if value:
            return value
        return cls.model_fields["type"].get_default()

    @property
    def raw(self) -> Message:
        if self._raw is None:
            raise AttributeError("raw property accessible only for incoming messages")
        return self._raw

    @property
    def service(self):
        return get_current_service()

    @property
    def log_context(self) -> Dict[str, Any]:
        return {"message_id": str(self.id)}

    def _set(self, name: str, value: Any):
        object.__setattr__(self, name, value)

    def set_source(self, value: str) -> None:
        self._set("source", value)

    def set_raw(self, value: Message):
        self._set("_raw", value)

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    @classmethod
    def new(cls, obj: D, **kwargs: Any):
        return cls(data=obj, **kwargs)

    @property
    def extra_span_attributes(self) -> Dict[str, str]:
        return {}

    @property
    def age(self) -> timedelta:
        return utc_now() - self.time

    def fail(self):
        self.raw.fail()

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        extra="allow",
        arbitrary_types_allowed=True,
        frozen=False,
    )
