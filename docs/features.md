## eventiq features

- Modern, `asyncio` based python 3.8+ syntax
- Minimal dependencies, only `anyio` and `pydantic` are required
- Automatic message parsing based on type annotations (like FastAPI)
- Code hot-reload
- Highly scalable: each service can process hundreds of tasks concurrently,
    all messages are load balanced between all instances by default
- Resilient - at least once delivery for all messages by default 
- Customizable & pluggable message encoders (json, msgpack, custom)
- Json formatted logger
- Multiple broker support (Nats, Kafka, Rabbitmq, Redis, PubSub, and more coming)
- Easily extensible via Middlewares and Plugins
- Cloud Events standard as base message structure (no more python specific `*args` and `**kwargs` in messages)
- AsyncAPI documentation generation from code
- Twelve factor app approach - stdout logging, configuration through environment variables
- Out-of-the-box integration with Prometheus (metrics) and OpenTelemetry (tracing)
- Application bootstrap via `.yaml` file (see examples/configuration)