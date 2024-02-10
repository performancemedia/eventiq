from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, Field
from pydantic_core import Url

SecurityType = Literal[
    "userPassword",
    "apiKey",
    "X509",
    "symmetricEncryption",
    "asymmetricEncryption",
    "httpApiKey",
    "http",
    "oauth2",
    "openIdConnect",
    "plain",
    "scramSha256",
    "scramSha512",
    "gssapi",
]


class BaseModel(_BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Reference(BaseModel):
    ref: str = Field(..., alias="$ref")


class ExternalDocumentation(BaseModel):
    url: Url
    description: str | None = None


OptExternalDocs = Union[ExternalDocumentation, Reference, None]


class Contact(BaseModel):
    name: str
    url: Url
    email: str


class License(BaseModel):
    name: str
    url: Url


class Tag(BaseModel):
    name: str
    description: str | None = None
    externalDocs: OptExternalDocs = None


Tags = list[Tag]


class Info(BaseModel):
    title: str
    version: str
    description: str | None = None
    termsOfService: Url | None = None
    license: License | None = None
    tags: Tags | None = None
    contact: Contact | None = None
    externalDocs: OptExternalDocs = None


class ServerVariable(BaseModel):
    enum: list[str] | None = None
    default: str | None = None
    description: str | None = None
    examples: list[str] | None = None


class OAuthFlow(BaseModel):
    authorizationUrl: str
    tokenUrl: str
    refreshUrl: str | None = None
    availableScopes: dict[str, str] | None = None


class OAuthFlows(BaseModel):
    implicit: OAuthFlow | None = None
    password: OAuthFlow | None = None
    clientCredentials: OAuthFlow | None = None
    authorizationObject: OAuthFlow | None = None


class SecurityScheme(BaseModel):
    type: SecurityType
    name: str
    description: str | None = None
    in_: str = Field(..., alias="in")
    scheme: str
    bearerFormat: str | None = None
    flows: OAuthFlows
    openIdConnectUrl: Url
    scopes: list[str] = []


class Server(BaseModel):
    host: str
    protocol: str
    protocolVersion: str | None = None
    pathname: str = ""
    description: str | None = None
    title: str | None = None
    summary: str | None = None
    variables: dict[str, Reference | ServerVariable] = {}
    security: list[Reference | SecurityScheme] = []
    tags: Tags | None = None
    externalDocs: OptExternalDocs = None
    # bindings: Optional[Reference]


#
# class Schema(BaseModel):
#     schemaFormat: str = "application/schema+json;version=draft-07"
#     spec: Any = Field(..., alias="schema")


class Message(BaseModel):
    name: str
    title: str
    contentType: str
    summary: str | None = None
    description: str | None = None
    payload: Reference | Any
    tags: Tags | None = None
    externalDocs: OptExternalDocs = None
    # headers: Union[Schema, Reference]
    # correlationId: Optional[Union[Reference, Any]]
    # traits: ...
    # bindings: ...


class Parameter(BaseModel):
    enum: list[str] | None = None
    default: str | None = None
    description: str | None = None
    examples: list[str] | None = None
    location: str | None = None


class Channel(BaseModel):
    address: str
    messages: dict[str, Message | Reference] = {}
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    servers: list[Reference] = []
    parameters: dict[str, Parameter | Reference] | None = None
    tags: Tags | None = None
    externalDocs: OptExternalDocs = None
    # bindings: Union[Reference, ChannelBinding, None]


class ReplyAddress(BaseModel):
    location: str
    description: str | None


class Reply(BaseModel):
    address: ReplyAddress | Reference
    channel: Reference | None = None
    messages: list[Reference] = []


class Operation(BaseModel):
    action: Literal["send", "receive"]
    channel: Reference
    title: str
    summary: str = ""
    description: str | None = None
    security: list[SecurityScheme | Reference] | None = None
    tags: Tags | None = None
    externalDocs: OptExternalDocs = None
    messages: list[Reference] = []
    reply: Reply | Reference | None = None
    # bindings: ...
    # traits: ...


class Components(BaseModel):
    schemas: dict[str, Reference | Any] | None = None
    servers: dict[str, Server | Reference] | None = None
    channels: dict[str, Channel | Reference] | None = None
    operations: dict[str, Operation | Reference] | None = None
    messages: dict[str, Message | Reference] | None = None
    securitySchemas: dict[str, SecurityScheme | Reference] | None = None
    serverVariables: dict[str, ServerVariable | Reference] | None = None
    parameters: dict[str, Parameter | Reference] | None = None
    replies: dict[str, Reply | Reference] | None = None
    replyAddresses: dict[str, ReplyAddress | Reference] | None = None
    externalDocs: dict[str, ExternalDocumentation | Reference] | None = None
    tags: dict[str, Tag | Reference] | None = None
    # correlationIds
    # operationTraits
    # messageTraits
    # serverBindings
    # channelBindings
    # operationBindings
    # messageBindings


class AsyncAPI(BaseModel):
    asyncapi: str = "3.0.0"
    info: Info
    servers: dict[str, Server | Reference] = {}
    defaultContentType: str | None = None
    channels: dict[str, Reference | Channel] = {}
    operations: dict[str, Reference | Operation] = {}
    components: Components = Field(default_factory=Components)
    logo: str = Field(
        "https://raw.githubusercontent.com/asyncapi/spec/master/assets/logo.png",
        alias="x-logo",
    )
