import asyncio
from typing import Sequence

from .service import Service


class ServiceRunner:
    """
    Service container for running multiple service instances in one process.
    :param services: Sequence of services to run
    """

    def __init__(self, services: Sequence[Service]) -> None:
        self.services = services

    def run(self, use_uvloop: bool = False, **kwargs) -> None:
        import aiorun

        aiorun.run(
            self._run(), shutdown_callback=self._stop, use_uvloop=use_uvloop, **kwargs
        )

    async def _run(self):
        await asyncio.gather(*[s.start() for s in self.services])

    async def _stop(self, *args, **kwargs):
        await asyncio.gather(*[s.stop() for s in self.services])
