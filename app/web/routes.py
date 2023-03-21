from app.web.application import Application
from app.web.views import ThemesView, MediaView, ThemeView, QuestionView


def setup_web_routes(app: Application):
    app.router.add_view("/themes", ThemesView)
    app.router.add_view("/themes/{theme_id}", ThemeView)
    app.router.add_view("/themes/{theme_id}/questions/{question_id}", QuestionView)
    app.router.add_view("/themes/{theme_id}/questions/{question_id}/media", MediaView)
