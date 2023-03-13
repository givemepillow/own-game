from app.bot.views import VIEWS
from app.web.application import Application


def setup_bot_routes(app: Application):
    for view in VIEWS:
        app.bot.dispatcher.register(view(app))
