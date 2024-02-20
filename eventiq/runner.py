import signal

import anyio
from anyio import CancelScope

from .logger import LoggerMixin
from .service import AbstractService


class ServiceRunner(LoggerMixin):
    """
    Service container for running multiple service instances in one process
    :param services: Sequence of services to run
    """

    def __init__(
        self, *services: AbstractService, enable_signal_handler: bool = True
    ) -> None:
        self.services = services
        self.enable_signal_handler = enable_signal_handler

    async def run(self) -> None:
        try:
            async with anyio.create_task_group() as tg:
                if self.enable_signal_handler:
                    tg.start_soon(self.watch_for_signals, tg.cancel_scope)

                for service in self.services:
                    tg.start_soon(service.start, tg.cancel_scope)
        except Exception as e:
            self.logger.error("Error running services", exc_info=e)
        finally:
            await self.stop()

    async def watch_for_signals(self, scope: CancelScope) -> None:
        with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
            async for signum in signals:
                self.logger.info(f"Received signal {signum.name}")
                scope.cancel()

    async def stop(self):
        self.logger.info("Stopping services...")
        with anyio.move_on_after(25, shield=True):
            for service in self.services:
                try:
                    await service.stop()
                except Exception as e:
                    self.logger.warning("Error stopping service", exc_info=e)
        self.logger.info("Exiting...")
