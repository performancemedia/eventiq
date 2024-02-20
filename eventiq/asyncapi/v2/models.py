from typing import Any, Optional

from pydantic import AnyUrl, ConfigDict, Field
from pydantic import BaseModel as _BaseModel


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


class Ref(BaseModel):
    ref: str = Field(..., alias="$ref")


class Message(BaseModel):
    payload: Ref
    content_type: str = Field(..., alias="contentType")
    description: Optional[str] = None
    tags: Optional[list[Tag]] = None


class Operation(BaseModel):
    operation_id: str = Field(..., alias="operationId")
    summary: Optional[str] = None
    message: Ref
    tags: Optional[list[Tag]] = None


class Parameter(BaseModel):
    description: Optional[str] = None
    param_schema: dict[str, Any] = Field({"type": "string"}, alias="schema")
    location: Optional[str] = None


class ChannelItem(BaseModel):
    publish: Optional[Operation] = None
    subscribe: Optional[Operation] = None
    parameters: dict[str, Parameter] = {}


class Server(BaseModel):
    protocol: str
    url: Optional[str] = None
    protocol_version: str = Field("", alias="protocolVersion")
    description: Optional[str] = None


class Components(BaseModel):
    schemas: dict[str, Any] = {}
    messages: dict[str, Any] = {}


class AsyncAPI(BaseModel):
    asyncapi: str = "2.5.0"
    info: Info
    servers: dict[str, Server] = {}
    channels: dict[str, ChannelItem] = {}
    default_content_type: str = Field("application/json", alias="defaultContentType")
    components: Components
    tags: list[Tag] = []
