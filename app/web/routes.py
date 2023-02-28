from app.web.application import Application
from app.web.views import ThemeView


def setup_web_routes(app: Application):
    app.router.add_view("/themes", ThemeView)
