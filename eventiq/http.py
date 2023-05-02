from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import ConfigurationError

if TYPE_CHECKING:

    from fastapi import FastAPI

    from .service import Service


def include_service(
    app: FastAPI,
    service: Service,
    add_health_endpoint: bool = False,
    path: str = "/healthz",
) -> None:
    app.on_event("startup")(service.start)
    app.on_event("shutdown")(service.stop)

    if add_health_endpoint:
        from fastapi.responses import JSONResponse

        middlewares = [
            m for m in service.broker.middlewares if hasattr(m, "get_health_status")
        ]
        if len(middlewares) and middlewares[0]:
            m = middlewares[0]

            @app.get(path, response_class=JSONResponse)
            def get_health_status():
                """Return get broker connection status"""
                status = m.get_health_status()
                return (
                    JSONResponse({"status": "ok"})
                    if status
                    else JSONResponse({"status": "Connection error"}, status_code=503)
                )

        raise ConfigurationError("HealthCheckMiddleware expected")


def add_serve_async_api_endpoint(
    app: FastAPI, service: Service, endpoint: str = "/docs/asyncapi.json"
):
    from .asyncapi.generator import get_async_api_spec
    from .asyncapi.models import AsyncAPI

    spec = get_async_api_spec(service)

    @app.get(endpoint, response_model=AsyncAPI)
    def get_asyncapi_spec():
        """Return service Async API specification"""
        return spec
