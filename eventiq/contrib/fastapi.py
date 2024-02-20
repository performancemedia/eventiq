from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from ..logger import LoggerMixin
from ..plugins import Service, ServicePlugin


class StatusOk(BaseModel):
    status: Literal[200] = 200
    detail: Literal["ok"] = "ok"


class HealthCheckError(BaseModel):
    title: Literal["Service Unavailable"] = "Service Unavailable"
    status: Literal[503] = 503
    detail: Literal["Connection Error"] = "Connection Error"


STATUS_OK = StatusOk().model_dump()
HEALTHCHECK_ERROR = HealthCheckError().model_dump()


class FastAPIServicePlugin(ServicePlugin, LoggerMixin):
    """Integration with fastapi, allows running service alongside fastapi app"""

    def configure_app(
        self,
        app: FastAPI,
        run_service: bool = True,
        async_api_url: str | None = None,
        async_api_version: int = 3,
        healthcheck_url: str | None = None,
    ) -> None:
        app._service = self.service
        if run_service:
            self._add_run_service_events(app)

        else:
            self._add_broker_connect_events(app)

        if async_api_url:
            self._add_asyncapi_url(app, async_api_url, async_api_version)

        if healthcheck_url:
            self._add_healthcheck(app, healthcheck_url)

    def _add_run_service_events(self, app):
        @app.on_event("startup")
        async def create_service_task():
            asyncio.create_task(self.service.start())

        @app.on_event("shutdown")
        async def stop_service_task():
            await self.service.stop()

    def _add_broker_connect_events(self, app):
        @app.on_event("startup")
        async def connect_broker():
            await self.service.connect_all()

        @app.on_event("shutdown")
        async def disconnect_broker():
            await self.service.disconnect_all()

    def _add_asyncapi_url(self, app, async_api_url, version: int):
        from eventiq.asyncapi import resolve_generator
        from eventiq.asyncapi.utils import get_html

        get_async_api_spec = resolve_generator(version)

        content = get_html()

        @app.get(async_api_url, response_class=HTMLResponse, include_in_schema=False)
        def get_asyncapi_docs():
            return HTMLResponse(content=content)

        @app.get(
            f"{async_api_url}.html",
            response_class=HTMLResponse,
            include_in_schema=False,
        )
        def get_service_asyncapi_html():
            """Return service Async API specification"""
            spec = get_async_api_spec(self.service)
            return HTMLResponse(
                content=spec.model_dump_json(exclude_none=True, by_alias=True)
            )

        @app.get(
            f"{async_api_url}.json",
            response_class=JSONResponse,
            include_in_schema=False,
        )
        def get_asyncapi_json():
            spec = get_async_api_spec(self.service)
            return JSONResponse(
                content=spec.model_dump(exclude_none=True, by_alias=True)
            )

    def _add_healthcheck(self, app, healthcheck_url):
        @app.get(
            healthcheck_url,
            response_model=StatusOk,
            responses={503: {"model": HealthCheckError}},
            include_in_schema=False,
        )
        def get_broker_connection_status():
            try:
                for broker_name, broker in self.service.get_brokers():
                    if not broker.is_connected:
                        raise ConnectionError(
                            f"Broker {broker}: {broker_name} disconnected"
                        )
                return JSONResponse(
                    status_code=200,
                    content=STATUS_OK,
                )
            except Exception as e:
                self.logger.warning("Exception in healthcheck", exc_info=e)
                return JSONResponse(
                    status_code=503,
                    content=HEALTHCHECK_ERROR,
                )


def get_service(request: Request) -> Service:
    return request.app._service


def ProvideService():
    return Depends(get_service)
