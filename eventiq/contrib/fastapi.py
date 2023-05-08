from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ..asyncapi.generator import get_async_api_spec
from ..asyncapi.models import AsyncAPI
from ..plugins import Service, ServicePlugin


class FastAPIServicePlugin(ServicePlugin):
    """Integration with fastapi, allows"""

    def __init__(
        self,
        service: Service,
        app: FastAPI,
        async_api_url: str | None = None,
        healthcheck_url: str | None = None,
    ):
        super().__init__(service)
        app.on_event("startup")(service.start)
        app.on_event("shutdown")(service.stop)

        if async_api_url:

            @app.get(async_api_url, response_model=AsyncAPI)
            def get_service_asyncapi():
                """Return service Async API specification"""
                return get_async_api_spec(service)

        if healthcheck_url:

            @app.get(healthcheck_url, response_class=JSONResponse)
            def get_broker_connection_status():
                try:
                    res = self.service.broker.is_connected
                    if not res:
                        raise ValueError
                    return JSONResponse({"status": "ok"})
                except Exception:
                    return JSONResponse(
                        {"detail": "Service Unavailable", "status": 503},
                        status_code=503,
                    )
