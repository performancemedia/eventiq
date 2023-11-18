from typing import Any, Dict, List, Optional, Type

from pydantic import AnyUrl
from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, Field, model_validator

from eventiq.models import CloudEvent


class BaseModel(_BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ExtendableBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Info(BaseModel):
    title: str
    version: str


class ExternalDocumentation(ExtendableBaseModel):
    description: Optional[str] = None
    url: AnyUrl


class Tag(ExtendableBaseModel):
    name: str
    description: Optional[str] = None
    externalDocs: Optional[ExternalDocumentation] = None
    model_config = ConfigDict(extra="allow")


class PublishInfo(BaseModel):
    event_type: Type[CloudEvent]
    topic: str = ""
    kwargs: Dict[str, Any] = {}

    @model_validator(mode="after")
    def set_default_topic(self):
        if not self.topic:
            self.topic = self.event_type.model_fields["event_type"].get_default()
        return self

    @classmethod
    def s(cls, even_type: Type[CloudEvent], topic: Optional[str] = None, **kwargs: Any):
        return cls(event_type=even_type, topic=topic, kwargs=kwargs)


class Ref(BaseModel):
    ref: str = Field(..., alias="$ref")


class Message(BaseModel):
    payload: Ref
    content_type: str = Field(..., alias="contentType")
    description: Optional[str] = None
    tags: Optional[List[Tag]] = None


class Operation(BaseModel):
    operation_id: str = Field(..., alias="operationId")
    summary: Optional[str] = None
    message: Ref
    tags: Optional[List[Tag]] = None


class Parameter(BaseModel):
    description: Optional[str] = None
    param_schema: Dict[str, Any] = Field({"type": "string"}, alias="schema")
    location: Optional[str] = None


class ChannelItem(BaseModel):
    publish: Optional[Operation] = None
    subscribe: Optional[Operation] = None
    parameters: Dict[str, Parameter] = {}


class Server(BaseModel):
    protocol: str
    url: Optional[str] = None
    protocol_version: Optional[str] = Field(None, alias="protocolVersion")
    description: Optional[str] = None


class Components(BaseModel):
    schemas: Dict[str, Any] = {}
    messages: Dict[str, Any] = {}


class AsyncAPI(BaseModel):
    asyncapi: str = "2.5.0"
    info: Info
    servers: Dict[str, Server] = {}
    channels: Dict[str, ChannelItem] = {}
    default_content_type: str = Field("application/json", alias="defaultContentType")
    components: Components
    tags: Optional[List[Tag]] = None
