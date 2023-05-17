from typing import Any, Dict, List, Optional, Type

from pydantic import AnyUrl
from pydantic import BaseModel as _BaseModel
from pydantic import Field, validator

from eventiq.models import CloudEvent


class BaseModel(_BaseModel):
    class Config:
        allow_population_by_field_name = True


class ExtendableBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True
        extra = "allow"


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

    class Config:
        extra = "allow"


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
