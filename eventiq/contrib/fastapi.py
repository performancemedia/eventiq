from __future__ import annotations

import asyncio

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from ..asyncapi.generator import get_async_api_spec
from ..asyncapi.models import AsyncAPI
from ..plugins import Service, ServicePlugin


class FastAPIServicePlugin(ServicePlugin):
    """Integration with fastapi, allows running service alongside fastapi app"""

    def __init__(
        self,
        service: Service,
    ):
        super().__init__(service)
        self._task: asyncio.Task | None = None

    def configure_app(
        self,
        app: FastAPI,
        run_service: bool = True,
        async_api_url: str | None = None,
        healthcheck_url: str | None = None,
    ) -> None:
        app._service = self.service
        if run_service:
            self._add_run_service_events(app)

        else:
            self._add_broker_connect_events(app)

        if async_api_url:
            self._add_asyncapi_url(app, async_api_url)

        if healthcheck_url:
            self._add_healthcheck(app, healthcheck_url)

    def _add_run_service_events(self, app):
        @app.on_event("startup")
        async def create_service_task():
            self._task = asyncio.create_task(self.service.start())

        @app.on_event("shutdown")
        async def stop_service_task():
            if self._task:
                self._task.cancel()
                await asyncio.wait_for(self._task, timeout=15)
                await self.service.stop()

    def _add_broker_connect_events(self, app):
        @app.on_event("startup")
        async def connect_broker():
            await self.service.broker.connect()

        @app.on_event("shutdown")
        async def disconnect_broker():
            await self.service.broker.disconnect()

    def _add_asyncapi_url(self, app, async_api_url):
        @app.get(async_api_url, response_model=AsyncAPI)
        def get_service_asyncapi():
            """Return service Async API specification"""
            return get_async_api_spec(self.service)

    def _add_healthcheck(self, app, healthcheck_url):
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


def get_service(request: Request) -> Service:
    return request.app._service


def ProvideService():
    return Depends(get_service)
