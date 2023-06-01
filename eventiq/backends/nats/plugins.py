from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nats.js.errors import KeyNotFoundError
from nats.js.kv import KeyValue

from eventiq.backends.nats.broker import JetStreamBroker
from eventiq.middleware import Middleware
from eventiq.plugins import BrokerPlugin
from eventiq.types import ID, ResultBackend
from eventiq.utils import retry

if TYPE_CHECKING:
    from eventiq import Broker, CloudEvent, Consumer, Service


class _NatsJetStreamResultMiddleware(Middleware):
    def __init__(self, result_backend: JetStreamResultBackend):
        self.result_backend = result_backend

    async def after_service_start(self, broker: Broker, service: Service):
        self.result_backend.buckets[service.name] = await broker.js.create_key_value(  # type: ignore[attr-defined]
            bucket=service.name, **self.result_backend.options
        )

    @retry(max_retries=3, backoff=10)
    async def after_process_message(
        self,
        broker: Broker,
        service: Service,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ) -> None:
        """Store message result in JetStream K/V Store"""
        if not consumer.store_results:
            return

        kv = self.result_backend.buckets.get(service.name)

        if kv is None:
            self.logger.warning(f"Bucket {service.name} not found")
            return

        if exc is None:
            data = broker.encoder.encode(result)
        elif exc and self.result_backend.store_exceptions:
            data = broker.encoder.encode(
                {"type": type(exc).__name__, "detail": str(exc)}
            )
        else:
            return
        await kv.put(str(message.id), data)


class JetStreamResultBackend(BrokerPlugin[JetStreamBroker], ResultBackend):
    def __init__(
        self, broker: JetStreamBroker, store_exceptions: bool = False, **options: Any
    ):
        super().__init__(broker)
        self.store_exceptions = store_exceptions
        self.options = options
        self.broker.add_middleware(_NatsJetStreamResultMiddleware(self))
        self.buckets: dict[str, KeyValue] = {}

    @retry(max_retries=3)
    async def _get(self, kv: KeyValue, key: ID) -> Any:
        return await kv.get(str(key))

    async def get_result(self, service: str, message_id: ID) -> Any:
        kv = self.buckets.get(service)
        if kv is None:
            self.logger.warning(f"Bucket {service} not found")
            return

        try:
            data = await self._get(kv, message_id)
            return self.broker.encoder.decode(data.value)
        except KeyNotFoundError:
            self.logger.warning(f"Key {message_id} not found")
            return
