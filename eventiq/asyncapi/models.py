from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel as _BaseModel
from pydantic import Field

from eventiq.models import CloudEvent


class BaseModel(_BaseModel):
    class Config:
        allow_population_by_field_name = True


class Info(BaseModel):
    title: str
    version: str


class PublishInfo(BaseModel):
    topic: str
    event_type: Type[CloudEvent]
    kwargs: Dict[str, Any]


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


class ChannelItem(BaseModel):
    publish: Optional[Operation] = None
    subscribe: Optional[Operation] = None


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
