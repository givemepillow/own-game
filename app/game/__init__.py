from app.game.handlers import HANDLERS
from app.web.application import Application


def setup_handlers(app: Application):
    app.bus.register(HANDLERS)
