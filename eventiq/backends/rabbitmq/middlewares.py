from __future__ import annotations

from aio_pika import ExchangeType

from eventiq.backends.rabbitmq.broker import RabbitmqBroker
from eventiq.middleware import Middleware


class DeadLetterQueueMiddleware(Middleware[RabbitmqBroker]):
    def __init__(self, dlx_name: str = "dlx") -> None:
        self.dlx_name = dlx_name
        self._dlx_exchange = None

    async def after_broker_connect(self, broker: RabbitmqBroker) -> None:  # type: ignore[override]
        if not isinstance(broker, RabbitmqBroker):
            raise TypeError(
                f"RabbitmqBroker instance expected, got {type(broker).__name__}"
            )
        channel = await broker.connection.channel()
        self._dlx_exchange = await channel.declare_exchange(
            name=self.dlx_name, type=ExchangeType.HEADERS, auto_delete=True
        )
