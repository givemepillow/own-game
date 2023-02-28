from __future__ import annotations

import typing
from typing import Optional, Type
from abc import ABC, abstractmethod

from app.bot.updates import BotUpdate
from app.abc.bot import AbstractBot
from app.bot.signatures import AbstractSignature

if typing.TYPE_CHECKING:
    from app.web.bootstrap import Application


class BotView(ABC):
    signature: AbstractSignature
    update_type: Type[BotUpdate]

    def __init__(self, app: Application):
        self.app = app
        self.bot: Optional[AbstractBot] = None

    async def __call__(self, update: BotUpdate):
        self.bot = self.app.bot(update)
        await self.handle(update)

    @abstractmethod
    async def handle(self, update: BotUpdate):
        pass
