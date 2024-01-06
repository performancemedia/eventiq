from typing import Any, Dict, List, Literal, Optional, Union

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
    description: Optional[str] = None


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
    description: Optional[str] = None
    externalDocs: OptExternalDocs = None


Tags = List[Tag]


class Info(BaseModel):
    title: str
    version: str
    description: Optional[str] = None
    termsOfService: Optional[Url] = None
    license: Optional[License] = None
    tags: Optional[Tags] = None
    contact: Optional[Contact] = None
    externalDocs: OptExternalDocs = None


class ServerVariable(BaseModel):
    enum: Optional[List[str]] = None
    default: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[List[str]] = None


class OAuthFlow(BaseModel):
    authorizationUrl: str
    tokenUrl: str
    refreshUrl: Optional[str] = None
    availableScopes: Optional[Dict[str, str]] = None


class OAuthFlows(BaseModel):
    implicit: Optional[OAuthFlow] = None
    password: Optional[OAuthFlow] = None
    clientCredentials: Optional[OAuthFlow] = None
    authorizationObject: Optional[OAuthFlow] = None


class SecurityScheme(BaseModel):
    type: SecurityType
    name: str
    description: Optional[str] = None
    in_: str = Field(..., alias="in")
    scheme: str
    bearerFormat: Optional[str] = None
    flows: OAuthFlows
    openIdConnectUrl: Url
    scopes: List[str] = []


class Server(BaseModel):
    host: str
    protocol: str
    protocolVersion: Optional[str] = None
    pathname: str = ""  # TODO: maybe optional
    description: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    variables: Dict[str, Union[Reference, ServerVariable]] = {}
    security: List[Union[Reference, SecurityScheme]] = []
    tags: Optional[Tags] = None
    externalDocs: OptExternalDocs = None
    # bindings: Optional[Reference]


class Schema(BaseModel):
    schemaFormat: str = "application/schema+json;version=draft-07"
    spec: Any = Field(..., alias="schema")


class Message(BaseModel):
    name: str
    title: str
    contentType: str
    summary: Optional[str] = None
    description: Optional[str] = None
    payload: Union[Reference, Any]
    tags: Optional[Tags] = None
    externalDocs: OptExternalDocs = None
    # headers: Union[Schema, Reference]
    # correlationId: Optional[Union[Reference, Any]]
    # traits: ...
    # bindings: ...


class Parameter(BaseModel):
    enum: Optional[List[str]] = None
    default: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[List[str]] = None
    location: Optional[str] = None


class Channel(BaseModel):
    address: str
    messages: Dict[str, Union[Message, Reference]] = {}
    title: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    servers: List[Reference] = []
    parameters: Optional[Dict[str, Union[Parameter, Reference]]] = None
    tags: Optional[Tags] = None
    externalDocs: OptExternalDocs = None
    # bindings: Union[Reference, ChannelBinding, None]


class ReplyAddress(BaseModel):
    location: str
    description: Optional[str]


class Reply(BaseModel):
    address: Union[ReplyAddress, Reference]
    channel: Optional[Reference] = None
    messages: List[Reference] = []


class Operation(BaseModel):
    action: Literal["send", "receive"]
    channel: Reference
    title: str
    summary: str = ""
    description: Optional[str] = None
    security: Optional[List[Union[SecurityScheme, Reference]]] = None
    tags: Optional[Tags] = None
    externalDocs: OptExternalDocs = None
    messages: List[Reference] = []
    reply: Union[Reply, Reference, None] = None
    # bindings: ...
    # traits: ...


class Components(BaseModel):
    schemas: Optional[Dict[str, Union[Reference, Any]]] = None
    servers: Optional[Dict[str, Union[Server, Reference]]] = None
    channels: Optional[Dict[str, Union[Channel, Reference]]] = None
    operations: Optional[Dict[str, Union[Operation, Reference]]] = None
    messages: Optional[Dict[str, Union[Message, Reference]]] = None
    securitySchemas: Optional[Dict[str, Union[SecurityScheme, Reference]]] = None
    serverVariables: Optional[Dict[str, Union[ServerVariable, Reference]]] = None
    parameters: Optional[Dict[str, Union[Parameter, Reference]]] = None
    replies: Optional[Dict[str, Union[Reply, Reference]]] = None
    replyAddresses: Optional[Dict[str, Union[ReplyAddress, Reference]]] = None
    externalDocs: Optional[Dict[str, Union[ExternalDocumentation, Reference]]] = None
    tags: Optional[Dict[str, Union[Tag, Reference]]] = None
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
    servers: Dict[str, Union[Server, Reference]] = {}
    defaultContentType: Optional[str] = None
    channels: Dict[str, Union[Reference, Channel]] = {}
    operations: Dict[str, Union[Reference, Operation]] = {}
    components: Components = Field(default_factory=Components)
    logo: str = Field(
        "https://raw.githubusercontent.com/asyncapi/spec/master/assets/logo.png",
        alias="x-logo",
    )
