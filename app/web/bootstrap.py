from aiohttp_apispec import setup_aiohttp_apispec
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from app.bot import setup_bot

from app.utils.config import setup_config
from app.utils.logger import setup_logging
from app.web.middlewares import setup_middlewares
from app.store import setup_store
from app.web.routes import setup_web_routes
from app.bot.routes import setup_bot_routes
from app.game.handlers import setup_handlers

from app.web.application import Application

app = Application()


def app_factory() -> Application:
    setup_config(app)
    setup_logging(app)
    setup_session(app, EncryptedCookieStorage(app.config.session.key, max_age=60 * 60 * 3))
    setup_middlewares(app)
    setup_aiohttp_apispec(app, title="Own game", swagger_path="/api/docs")
    setup_store(app)
    setup_bot(app)
    setup_handlers(app)
    setup_web_routes(app)
    setup_bot_routes(app)
    return app
