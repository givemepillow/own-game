from typing import final
from abc import ABC, abstractmethod
from logging import getLogger

from app.web.application import Application


class CleanupCTX(ABC):
    def __init__(self, app: Application):
        self.app = app
        self.logger = getLogger(self.__class__.__name__)
        app.cleanup_ctx.append(self._cleanup)

    @abstractmethod
    async def on_startup(self):
        ...

    @abstractmethod
    async def on_shutdown(self):
        ...

    @final
    async def _cleanup(self, _: Application):
        await self._on_startup()
        yield
        await self._on_shutdown()

    @final
    async def _on_startup(self):
        self.logger.info(f"starting up {self.__class__.__name__}...")
        await self.on_startup()

    @final
    async def _on_shutdown(self):
        self.logger.info(f"shutting down {self.__class__.__name__}...")
        await self.on_shutdown()
