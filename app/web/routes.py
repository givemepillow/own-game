from app.web.application import Application
from app.web.views import ThemeView, MediaView


def setup_web_routes(app: Application):
    app.router.add_view("/themes", ThemeView)
    app.router.add_view("/themes/{theme_id}/questions/{question_id}/media", MediaView)
