from aiohttp_apispec import setup_aiohttp_apispec

from app.bot import setup_bot

from app.utils.config import setup_config
from app.utils.logger import setup_logging
from app.web.middlewares import setup_middlewares
from app.store import setup_store
from app.web.routes import setup_web_routes

from app.web.application import Application

app = Application()


def app_factory() -> Application:
    setup_config(app)
    setup_logging(app)
    setup_middlewares(app)
    setup_aiohttp_apispec(app, title="Own game", swagger_path="/api/docs")
    setup_store(app)
    setup_bot(app)
    setup_web_routes(app)
    return app
