## eventiq features

- Modern, `asyncio` based python 3.7+ syntax
- Minimal dependencies, only `pydantic` and `async_timeout` are required
- Automatic message parsing based on type annotations (like FastAPI)
- Highly scalable: each service can process hundreds of tasks concurrently,
    all messages are load balanced between all instances by default
- Resilient - at least once delivery for all messages by default 
- Customizable & pluggable encoders (json, msgpack, custom)
- Multiple broker support (Nats, Kafka, Rabbitmq, Redis, PubSub, and more coming)
- Easily extensible via Middlewares and Plugins
- Cloud Events standard as base message structure (no more python specific `*args` and `**kwargs` in messages)
- AsyncAPI documentation generation from code
