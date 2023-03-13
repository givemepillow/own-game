from abc import ABC, abstractmethod

from app.abc.message import Message
from app.web.application import Application


class Handler(ABC):
    def __init__(self, app: Application):
        self.app = app

    async def __call__(self, msg: Message):
        await self.handler(msg)

    @abstractmethod
    async def handler(self, msg: Message):
        pass
