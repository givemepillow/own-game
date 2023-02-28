import typing
from logging import getLogger

from app.abc.bot_view import BotView
from app.bot.updates import BotUpdate


class Dispatcher:
    """
    Регистрирует обработчики обновлений и ищет подходящий для каждого пришедшего обновления.
    """

    def __init__(self):
        self.logger = getLogger(self.__class__.__name__)
        self._handlers: dict[typing.Type[BotUpdate], list[BotView]] = dict()

    def register(self, handler: BotView) -> typing.NoReturn:
        self._handlers.setdefault(handler.update_type, []).append(handler)

    async def handle(self, update: BotUpdate) -> typing.NoReturn:

        for handler in self._handlers.get(type(update), []):

            if handler.signature.match(update):
                await handler(update)
                break
        else:
            self.logger.info(f" matching handler was NOT found for {update}")
