
## Available middlewares

- `DebugMiddleware` - Logging every middleware function
- `ErrorHandlerMiddleware` - Custom error handling
- `PrometheusMiddleware` - Prometheus exporter of message processing metrics
- `HealthCheckMiddleware` - Broker connection healthcheck middleware
- `RetryMiddleware` - Automatic message retries middleware

## Writing custom middleware

1. Subclass from `eventiq.Middleware`
2. Implement any of the following methods

::: eventiq.middleware.Middleware
    handler: python
    options:
      show_root_heading: true
      show_source: false