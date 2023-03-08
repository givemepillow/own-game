from __future__ import annotations
import typing

from aiohttp.web import (
    Application as AiohttpApplication,
    Request as AiohttpRequest,
    View as AiohttpView,
)

if typing.TYPE_CHECKING:
    from app.utils.config import Config
    from app.store import Store
    from app.bot.proxy import BotProxy
    from app.store.bus import MessageBus


class Application(AiohttpApplication):
    @property
    def config(self) -> Config:
        return self['config']

    @property
    def store(self) -> Store:
        return self['store']

    @property
    def bot(self) -> BotProxy:
        return self['bot_proxy']

    @property
    def bus(self) -> MessageBus:
        return self['bus']


class Request(AiohttpRequest):
    @property
    def app(self) -> Application:
        return super().app()


class View(AiohttpView):
    @property
    def request(self) -> Request:
        return super().request

    @property
    def data(self) -> dict:
        return self.request.get("data", {})

    @property
    def app(self) -> Application:
        return self.request.app
