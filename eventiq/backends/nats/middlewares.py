from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nats.js.errors import KeyNotFoundError
from nats.js.kv import KeyValue

from eventiq.backends.nats.broker import JetStreamBroker
from eventiq.middleware import Middleware
from eventiq.utils.functools import retry_async

if TYPE_CHECKING:
    from eventiq.broker import Broker
    from eventiq.consumer import Consumer
    from eventiq.models import CloudEvent
    from eventiq.types import Encoder


class NatsJetStreamResultMiddleware(Middleware):
    def __init__(
        self,
        bucket: str,
        encoder: Encoder | None = None,
        store_exceptions: bool = False,
        **kv_options: Any,
    ):
        self.bucket = bucket
        self.store_exceptions = store_exceptions
        if encoder is None:
            from eventiq.encoders import get_default_encoder

            encoder = get_default_encoder()
        self.encoder = encoder
        self.options = kv_options
        self._kv = None

    @property
    def kv(self) -> KeyValue:
        if self._kv is None:
            raise ValueError("Middleware not configured")
        return self._kv

    @retry_async(max_retries=3, backoff=5)
    async def get(self, key: str) -> Any | None:
        kv = await self.kv.get(key)
        return self.encoder.decode(kv.value)

    async def get_or_none(self, key: str):
        try:
            return await self.get(key)
        except KeyNotFoundError:
            self.logger.warning(f"Key {key} not found")
            return None

    async def get_message_result(
        self, consumer_name: str, message_id: str
    ) -> Any | None:
        # TODO: timeout
        return await self.get(f"{consumer_name}:{message_id}")

    async def after_broker_connect(self, broker: Broker) -> None:
        if isinstance(broker, JetStreamBroker):
            self._kv = await broker.js.create_key_value(
                bucket=self.bucket, **self.options
            )
        else:
            self.logger.warning("Expected JetstreamBroker, got %s", type(broker))

    @retry_async(max_retries=3, backoff=10)
    async def after_process_message(
        self,
        broker: JetStreamBroker,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ):
        """Store message result in JetStream K/V Store"""
        if consumer.options.get("store_results"):
            if exc is None:

                data = self.encoder.encode(result)
                await self.kv.put(f"{consumer.name}:{message.id}", data)
            elif exc and self.store_exceptions:
                data = self.encoder.encode(
                    {"type": type(exc).__name__, "detail": str(exc)}
                )
                await self.kv.put(f"{consumer.name}:{message.id}", data)
