import asyncio
from abc import ABC, abstractmethod

from aiolimiter import AsyncLimiter

from app.abc.bot import AbstractBot
from app.abc.message import Message
from app.utils.limiter import Limiter
from app.web.application import Application


class Handler(ABC):
    lock = Limiter(lambda: asyncio.Lock())
    limiter = Limiter(lambda: AsyncLimiter(max_rate=19, time_period=60))

    def __init__(self, app: Application):
        self.app = app
        self.bot: AbstractBot | None = None

    async def __call__(self, msg: Message):
        if not self.limiter[msg.update.chat_id].has_capacity():
            return

        if self.lock[msg.update.chat_id].locked():
            return

        self.bot = self.app.bot(msg.update, self.limiter[msg.update.chat_id])

        await self.handler(msg)

    @abstractmethod
    async def handler(self, msg: Message):
        pass
