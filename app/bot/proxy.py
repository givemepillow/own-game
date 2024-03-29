from aiolimiter import AsyncLimiter

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

    def __call__(self, update: BotUpdate, limiter: AsyncLimiter) -> AbstractBot:
        if update.origin == Origin.TELEGRAM:
            return TelegramBot(self._telegram_api, update, limiter)
        return VkBot(self._vk_api, update)
