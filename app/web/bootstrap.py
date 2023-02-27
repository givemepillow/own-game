from aiohttp_apispec import setup_aiohttp_apispec

from app.utils.config import setup_config
from app.utils.logger import setup_logging
from app.web.application import Application
from app.web.middlewares import setup_middlewares

app = Application()


def app_factory() -> Application:
    setup_config(app)
    setup_logging(app)
    setup_middlewares(app)
    setup_aiohttp_apispec(
        app, title="Own game", url="/docs/json", swagger_path="/api/docs"
    )
    return app
