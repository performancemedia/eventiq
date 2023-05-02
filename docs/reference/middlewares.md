List of built-in middlewares

::: eventiq.middlewares.debug.DebugMiddleware
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.middlewares.error.ErrorHandlerMiddleware
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.middlewares.healthcheck.HealthCheckMiddleware
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.middlewares.prometheus.PrometheusMiddleware
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.middlewares.retries.RetryMiddleware
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: eventiq.middlewares.opentelemetry.OpenTelemetryMiddleware
    handler: python
    options:
      show_root_heading: true
      show_source: true