from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventiq.middleware import Middleware
from eventiq.utils.datetime import current_millis

if TYPE_CHECKING:
    from prometheus_client.registry import CollectorRegistry

    from eventiq import Broker, CloudEvent, Consumer, RawMessage, Service


DEFAULT_BUCKETS = (
    5,
    10,
    25,
    50,
    75,
    100,
    250,
    500,
    750,
    1000,
    2500,
    5000,
    7500,
    10000,
    30000,
    60000,
    600000,
    900000,
    float("inf"),
)


class PrometheusMiddleware(Middleware):
    def __init__(
        self,
        run_server: bool = False,
        registry: CollectorRegistry | None = None,
        buckets: tuple[float] | None = None,
        server_host: str = "0.0.0.0",  # nosec
        server_port: int = 8888,
    ):
        from prometheus_client import REGISTRY, Counter, Gauge, Histogram

        self.run_server = run_server
        self.registry = registry or REGISTRY
        self.buckets = buckets or DEFAULT_BUCKETS
        self.server_host = server_host
        self.server_port = server_port
        self.message_start_times: dict[str, int] = {}
        self.service_name: str | None = None
        self.in_progress = Gauge(
            "messages_in_progress",
            "Total number of messages being processed.",
            ["topic", "service", "consumer"],
            registry=self.registry,
        )
        self.total_messages = Counter(
            "messages_total",
            "Total number of messages processed.",
            ["topic", "service", "consumer"],
            registry=self.registry,
        )
        self.total_skipped_messages = Counter(
            "messages_skipped_total",
            "Total number of messages skipped processing.",
            registry=self.registry,
        )
        self.total_messages_published = Counter(
            "messages_published_total",
            "Total number of messages published",
            ["topic", "service"],
            registry=self.registry,
        )
        self.total_errored_messages = Counter(
            "message_error_total",
            "Total number of errored messages.",
            ["topic", "service", "consumer"],
            registry=self.registry,
        )
        self.total_rejected_messages = Counter(
            "message_rejected_total",
            "Total number of messages rejected",
            ["topic", "service", "consumer"],
            registry=self.registry,
        )
        self.message_durations = Histogram(
            "message_duration_ms",
            "Time spend processing message",
            ["topic", "service", "consumer"],
            registry=self.registry,
            buckets=self.buckets,
        )

    async def before_service_start(self, broker: Broker, service: Service):
        self.service_name = service.name

    async def before_process_message(
        self, broker: Broker, consumer: Consumer, message: CloudEvent
    ):
        labels = (consumer.topic, self.service_name, consumer.name)
        self.in_progress.labels(*labels).inc()
        self.message_start_times[message.id] = current_millis()

    async def after_process_message(
        self,
        broker: Broker,
        consumer: Consumer,
        message: CloudEvent,
        result: Any | None = None,
        exc: Exception | None = None,
    ):
        labels = (consumer.topic, self.service_name, consumer.name)
        self.in_progress.labels(*labels).dec()
        self.total_messages.labels(*labels).inc()
        if exc:
            self.total_errored_messages.labels(*labels).inc()

        message_start_time = self.message_start_times.pop(message.id, current_millis())
        message_duration = current_millis() - message_start_time
        self.message_durations.labels(*labels).observe(message_duration)

    async def after_skip_message(
        self, broker: Broker, consumer: Consumer, message: CloudEvent
    ) -> None:
        labels = (consumer.topic, self.service_name, consumer.name)
        self.total_skipped_messages.labels(*labels).inc()

    async def after_publish(self, broker: Broker, message: CloudEvent, **kwargs):
        self.total_messages_published.labels(message.topic, message.source).inc()

    async def after_nack(self, broker: Broker, consumer: Consumer, message: RawMessage):
        labels = (consumer.topic, self.service_name, consumer.name)
        self.total_rejected_messages.labels(*labels).inc()

    async def after_broker_connect(self, broker: Broker):
        if self.run_server:
            from prometheus_client import start_http_server

            start_http_server(
                self.server_port, self.server_host, registry=self.registry
            )
