import typing

from app.bot.proxy import BotProxy

if typing.TYPE_CHECKING:
    from app.web.application import Application

__all__ = ['setup_bot']


def setup_bot(app: "Application"):
    app['bot_proxy'] = BotProxy(app)
