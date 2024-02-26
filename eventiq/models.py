from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Generic, Literal, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import AnyUrl, BaseModel, Field, PrivateAttr, field_validator
from pydantic.fields import FieldInfo
from pydantic_core.core_schema import ValidationInfo

from .message import Message
from .utils import get_topic_regex, utc_now

if TYPE_CHECKING:
    from .service import Service


D = TypeVar("D", bound=Any)


class CloudEvent(BaseModel, Generic[D]):
    """Base Schema for all messages"""

    specversion: str = "1.0"
    content_type: str = Field(
        "application/json", alias="datacontenttype", description="Message content type"
    )
    id: UUID = Field(default_factory=uuid4, description="Event ID", repr=True)
    time: datetime = Field(default_factory=utc_now, description="Event created time")
    topic: str = Field(
        None,
        alias="subject",
        description="Message subject (topic)",
        validate_default=True,
    )
    type: str = Field(None, description="Event type", validate_default=True)
    source: Optional[str] = Field(None, description="Event source (app)")
    data: D = Field(..., description="Event payload")
    dataschema: Optional[AnyUrl] = Field(None, description="Data schema URI")
    tracecontext: dict[str, str] = Field({}, description="Distributed tracing context")
    dataref: Optional[str] = Field(
        None, description="Optional reference (URI) to event payload"
    )

    _raw: Optional[Any] = PrivateAttr(None)
    _service: Optional["Service"] = PrivateAttr(None)
    _headers: dict[str, str] = PrivateAttr({})
    _delay: Optional[int] = PrivateAttr(None)

    def __init_subclass__(
        cls,
        abstract: bool = False,
        topic: Optional[str] = None,
        validate_topic: bool = False,
        **kwargs: Any,
    ):
        if not abstract:
            if topic:
                kw = {
                    "alias": "subject",
                    "description": "Message subject",
                    "validate_default": True,
                }
                if any(k in topic for k in ("{", "}", "*", ">")):
                    kw.update(
                        {
                            "annotation": str,
                            "default": topic,
                        }
                    )
                    if validate_topic:
                        kw["pattern"] = get_topic_regex(topic)
                else:
                    kw.update(
                        {
                            "annotation": Literal[topic],
                            "default": topic,
                        }
                    )

                cls.model_fields["topic"] = FieldInfo(**kw)
            super().__init_subclass__(**kwargs)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CloudEvent):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        if self.type == type(self).__name__:
            return f"{self.type}(topic={self.topic}, id={self.id})"
        return (
            f"{type(self).__name__}(type={self.type}, topic={self.topic}, id={self.id})"
        )

    def __repr__(self) -> str:
        return str(self)

    @classmethod
    def get_default_topic(cls) -> Optional[str]:
        return cls.model_fields["topic"].get_default()

    @classmethod
    def get_default_content_type(cls) -> Optional[str]:
        return cls.model_fields["content_type"].get_default()

    @field_validator("type", mode="before")
    @classmethod
    def get_default_type(cls, value, info: ValidationInfo):
        if value is None:
            return cls.__name__
        return value

    @property
    def raw(self) -> Message:
        if self._raw is None:
            raise ValueError("raw property accessible only for incoming messages")
        return self._raw

    @raw.setter
    def raw(self, value: Message) -> None:
        self._raw = value

    @property
    def service(self) -> "Service":
        if self._service is None:
            raise ValueError("Not in the service context")
        return self._service

    @service.setter
    def service(self, value: "Service") -> None:
        self._service = value

    @property
    def context(self) -> dict[str, Any]:
        return self.service.context

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    @classmethod
    def new(cls, obj: D, *, headers: Optional[dict[str, str]] = None, **kwargs: Any):
        self = cls(data=obj, **kwargs)
        if headers:
            self.set_headers(headers)
        return self

    @property
    def extra_span_attributes(self) -> dict[str, str]:
        return {}

    @property
    def age(self) -> timedelta:
        return utc_now() - self.time

    @property
    def headers(self) -> dict[str, str]:
        if self._raw:
            return self.raw.headers
        return self._headers

    def set_header(self, key: str, value: str) -> None:
        if self._raw:
            raise ValueError("Cannot set headers for incoming message")
        self._headers[key] = value

    def set_default_header(self, key: str, value: str) -> None:
        if self._raw:
            raise ValueError("Cannot set headers for incoming message")
        self._headers.setdefault(key, value)

    def set_headers(self, headers: dict[str, str]) -> None:
        if self._raw:
            raise ValueError("Cannot set headers for incoming message")
        self._headers.update(headers)

    @property
    def delay(self) -> Optional[int]:
        if self._raw:
            return self.raw.delay
        return self._delay

    @delay.setter
    def delay(self, value: int) -> None:
        if value < 0:
            raise ValueError("Cannot set negative delay")
        if self._raw:
            self._raw.delay = value
        else:
            self._delay = value

    def fail(self) -> None:
        self.raw.fail()

    @property
    def failed(self) -> bool:
        return self.raw.failed

    model_config = {
        "use_enum_values": True,
        "populate_by_name": True,
        "extra": "allow",
        "arbitrary_types_allowed": True,
    }


class Event(CloudEvent[D], abstract=True):
    pass


class Command(CloudEvent[D], abstract=True):
    pass


class Query(CloudEvent[D], abstract=True):
    pass
