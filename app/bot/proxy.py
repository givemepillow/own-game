from functools import singledispatchmethod

from app.abc.bot import AbstractBot
from app.bot.enums import Origin
from app.bot.telegram.bot import TelegramBot
from app.bot.updates import BotUpdate

from app.bot.vk.accessor import VkAPIAccessor
from app.bot.telegram.accessor import TelegramAPIAccessor
from app.bot.dispatcher import Dispatcher
from app.bot.vk.bot import VkBot

from app.web.application import Application


class BotProxy:
    def __init__(self, app: Application):
        self.dispatcher = Dispatcher()

        self._telegram_api = TelegramAPIAccessor(app)
        self._vk_api = VkAPIAccessor(app)

    @singledispatchmethod
    def __call__(self, obj: object) -> AbstractBot:
        pass

    @__call__.register
    def _(self, origin: Origin) -> AbstractBot:
        print(f"{origin=}")
        if origin == Origin.TELEGRAM:
            return TelegramBot(self._telegram_api)
        return VkBot(self._vk_api)

    @__call__.register
    def _(self, update: BotUpdate) -> AbstractBot:
        if update.origin == Origin.TELEGRAM:
            return TelegramBot(self._telegram_api, update)
        return VkBot(self._vk_api, update)
