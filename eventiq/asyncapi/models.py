from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel as _BaseModel
from pydantic import Field, validator

from eventiq.models import CloudEvent


class BaseModel(_BaseModel):
    class Config:
        allow_population_by_field_name = True


class Info(BaseModel):
    title: str
    version: str


class PublishInfo(BaseModel):
    event_type: Type[CloudEvent]
    topic: str
    kwargs: Dict[str, Any] = {}

    @validator("topic", always=True, pre=True, allow_reuse=True)
    def set_default_topic(cls, v, values):
        if v is None:
            v = values["event_type"].__fields__["topic"].get_default()
        return v

    @classmethod
    def s(cls, even_type: Type[CloudEvent], topic: Optional[str] = None, **kwargs: Any):
        return cls(event_type=even_type, topic=topic, **kwargs)


class PayloadRef(BaseModel):
    ref: str = Field(..., alias="$ref")


class Message(BaseModel):
    message_id: str = Field(..., alias="messageId")
    payload: PayloadRef
    content_type: str = Field(..., alias="contentType")
    description: Optional[str] = None
    tags: List[str] = []


class Operation(BaseModel):
    summary: Optional[str] = None
    message: Message


class Parameter(BaseModel):
    description: Optional[str] = None
    param_schema: Dict[str, Any] = Field({"type": "string"}, alias="schema")
    location: Optional[str] = None


class ChannelItem(BaseModel):
    publish: Optional[Operation] = None
    subscribe: Optional[Operation] = None
    parameters: Dict[str, Parameter] = {}


class Server(BaseModel):
    url: Optional[str] = None
    protocol: str
    description: Optional[str] = None


class ExternalDocs(BaseModel):
    description: Optional[str] = None
    url: str


class Tag(BaseModel):
    name: str
    description: Optional[str] = None
    external_docs: Optional[str] = Field(None, alias="externalDocs")


class Components(BaseModel):
    schemas: Dict[str, Any]


class AsyncAPI(BaseModel):
    asyncapi: str = "2.5.0"
    info: Info
    servers: Dict[str, Server] = {}
    channels: Dict[str, ChannelItem] = {}
    default_content_type: str = Field("application/json", alias="defaultContentType")
    components: Components
