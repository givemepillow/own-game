from __future__ import annotations

import typing
from typing import Type
from abc import ABC, abstractmethod

from app.bot.updates import BotUpdate
from app.bot.signatures import AbstractSignature

if typing.TYPE_CHECKING:
    from app.web.bootstrap import Application


class BotView(ABC):
    signature: AbstractSignature
    update_type: Type[BotUpdate]

    def __init__(self, app: Application):
        self.app = app

    async def __call__(self, update: BotUpdate):
        await self.handle(update)

    @abstractmethod
    async def handle(self, update: BotUpdate):
        pass
