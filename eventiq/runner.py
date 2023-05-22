import signal
from typing import Sequence

import anyio

from .logger import LoggerMixin
from .service import Service


class ServiceRunner(LoggerMixin):
    """
    Service container for running multiple service instances in one process
    :param services: Sequence of services to run
    """

    def __init__(self, services: Sequence[Service]) -> None:
        self.services = services

    async def run(self):

        async with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
            async with anyio.create_task_group() as tg:
                try:
                    for service in self.services:
                        tg.start_soon(service.start)
                except Exception as e:
                    self.logger.exception("Unhandled exception", exc_info=e)
                    return

                async for _ in signals:
                    self.logger.info("Exiting...")
                    await tg.cancel_scope.cancel()
                    async with anyio.move_on_after(30, shield=True):
                        for service in self.services:
                            await service.stop()
                    return
